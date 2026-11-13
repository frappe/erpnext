# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""The supplier portal's server side: what its pages read, and the quote a supplier sends. Each
endpoint chooses its own fields, so a supplier receives what their page shows and nothing else --
above all, never the other suppliers invited to the same request for quotation, nor their quotes."""

from contextlib import contextmanager

import frappe
from frappe import _
from frappe.printing.doctype.print_format.classic_converter import convert_classic_to_beta
from frappe.printing.layout import iter_fields, iter_zones
from frappe.query_builder.functions import Max, Min
from frappe.rate_limiter import rate_limit
from frappe.translate import get_translation_version
from frappe.utils import add_days, cint, date_diff, escape_html, flt, getdate, today
from frappe.utils.html_utils import sanitize_html

from erpnext.accounts.doctype.sales_invoice.services.status import get_total_in_party_account_currency
from erpnext.buying.doctype.request_for_quotation.mapper import (
	add_items,
	get_quotable_rfq,
	validate_existing_supplier_quotation,
)
from erpnext.controllers.website_list_for_contact import get_parents_for_user

# The documents a supplier sees, by the field naming their supplier. Only submitted ones: a draft is
# not the supplier's business, and a cancelled one is nobody's.
SUPPLIER_DOCTYPES = {
	"Supplier Quotation": "supplier",
	"Purchase Order": "supplier",
	"Purchase Receipt": "supplier",
	"Purchase Invoice": "supplier",
	"Payment Entry": "party",
}

SUPPLIER_EXTRA_FILTERS = {"Payment Entry": [["party_type", "=", "Supplier"]]}

# the RFQ's own fields: its `suppliers` table names every supplier invited, so it is never read
RFQ_LIST_FIELDS = ("name", "transaction_date", "schedule_date", "company")

RFQ_FIELDS = (
	"name",
	"transaction_date",
	"schedule_date",
	"company",
	"message_for_supplier",
	"terms",
	"incoterm",
	"named_place",
	"billing_address_display",
	"shipping_address_display",
)

# not the warehouse, project, cost centre or material request: those are the buyer's own
RFQ_ITEM_FIELDS = ("name", "item_code", "item_name", "description", "qty", "uom", "schedule_date")

QUOTE_FIELDS = (
	"name",
	"amended_from",
	"docstatus",
	"status",
	"transaction_date",
	"valid_till",
	"quotation_number",
	"currency",
	"total",
	"grand_total",
	"rounded_total",
	"rounding_adjustment",
	"terms",
)

QUOTE_LIST_FIELDS = (
	"name",
	"status",
	"transaction_date",
	"valid_till",
	"quotation_number",
	"currency",
	"grand_total",
	"rounded_total",
	"company",
)

# what the quote page shows besides QUOTE_FIELDS: the buyer's addresses and the total in words
QUOTE_PAGE_FIELDS = (
	*QUOTE_FIELDS,
	"company",
	"in_words",
	"discount_amount",
	"apply_discount_on",
	"billing_address_display",
	"shipping_address_display",
)

QUOTE_ITEM_FIELDS = (
	"request_for_quotation_item",
	"qty",
	"price_list_rate",
	"discount_percentage",
	"rate",
	"amount",
	"expected_delivery_date",
	# how much of the line the buyer has ordered, across all their orders from it
	"ordered_qty",
)

# the lines of an order, receipt or invoice; never the warehouse, cost centre or project: the buyer's own
ITEM_FIELDS = ("item_code", "item_name", "description", "qty", "uom", "rate", "amount")

TAX_FIELDS = ("description", "tax_amount", "included_in_print_rate", "add_deduct_tax")

# what a priced document's totals column needs
TOTAL_FIELDS = (
	"currency",
	"total",
	"grand_total",
	"rounded_total",
	"rounding_adjustment",
	"discount_amount",
	"apply_discount_on",
	"in_words",
	"terms",
)

ORDER_LIST_FIELDS = (
	"name",
	"status",
	"transaction_date",
	"schedule_date",
	"per_received",
	"grand_total",
	"rounded_total",
	"currency",
	"company",
)

ORDER_FIELDS = (
	"name",
	"status",
	"transaction_date",
	"schedule_date",
	"per_received",
	"per_billed",
	"company",
	"incoterm",
	"named_place",
	"billing_address_display",
	"shipping_address_display",
	*TOTAL_FIELDS,
)

# the quotation each line came from, for the order page's "From quotation" link
ORDER_ITEM_FIELDS = (*ITEM_FIELDS, "schedule_date", "received_qty", "supplier_part_no", "supplier_quotation")

RECEIPT_LIST_FIELDS = ("name", "status", "posting_date", "is_return", "total_qty", "company")

RECEIPT_FIELDS = (
	"name",
	"status",
	"posting_date",
	"is_return",
	"return_against",
	"company",
	"currency",
	"grand_total",
	"per_billed",
	"supplier_delivery_note",
	"lr_no",
	"lr_date",
	"transporter_name",
	"shipping_address_display",
	"terms",
)

# a receipt page shows quantities, not prices, and links each line to its order
RECEIPT_ITEM_FIELDS = (
	"item_code",
	"item_name",
	"description",
	"qty",
	"rejected_qty",
	"uom",
	"purchase_order",
)

INVOICE_LIST_FIELDS = (
	"name",
	"status",
	"posting_date",
	"due_date",
	"bill_no",
	"outstanding_amount",
	"is_return",
	"grand_total",
	"rounded_total",
	"currency",
	"company",
)

INVOICE_FIELDS = (
	"name",
	"status",
	"posting_date",
	"due_date",
	"bill_no",
	"bill_date",
	"outstanding_amount",
	"is_return",
	# a debit note names the invoice it corrects
	"return_against",
	"company",
	# outstanding and payments are kept in this one, which can differ from the invoice's
	"party_account_currency",
	"billing_address_display",
	"shipping_address_display",
	*TOTAL_FIELDS,
)

# the order each line came from, for the invoice page's "From order" link
INVOICE_ITEM_FIELDS = (*ITEM_FIELDS, "purchase_order")

# Purchase Order statuses while the order is still running
ACTIVE_ORDER_STATUSES = ("To Receive and Bill", "To Receive", "To Bill", "To Pay", "On Hold")

# of those, the ones the supplier delivers on: the buyer paused an order On Hold, and owes the
# advance an order To Pay waits for
DELIVERING_ORDER_STATUSES = tuple(
	status for status in ACTIVE_ORDER_STATUSES if status not in ("On Hold", "To Pay")
)

# ERPNext marks an invoice overdue once any instalment is late; `due_date` is only the last one's
OVERDUE_INVOICE_STATUSES = ("Overdue",)

# a quotation the supplier can still replace with a revision: sent, and nothing ordered from it yet
REVISABLE_STATUSES = ("Submitted",)

# the longest supplier's reference a quote keeps, as a Data field does
QUOTATION_NUMBER_LENGTH = 140

# the page sizes a supplier can pick under a list, as on the customer portal; the first is the default
LIST_PAGE_LENGTHS = (20, 50, 100)
LIST_PAGE_LENGTH = LIST_PAGE_LENGTHS[0]

# Each list page: its tabs, what its search looks at, and which documents float to the top (by
# `deadline`, soonest first) before the rest, newest first. `scope` gives the filters for a tab's
# value, limited to the user's suppliers, and anything each row carries besides its fields.
LIST_PAGES = {
	"rfqs": {
		"doctype": "Request for Quotation",
		"fields": RFQ_LIST_FIELDS,
		"date_field": "transaction_date",
		"tabs": {"To quote": "Pending", "All": None, "Quoted": "Received"},
		"search": ("name",),
		"scope": lambda: _rfq_scope(),
		# not quoted yet, and the goods are needed within a week (or already were)
		"urgent": lambda: [["schedule_date", "<=", add_days(today(), 7)]],
		"urgent_status": "Pending",
		"deadline": "schedule_date",
	},
	"quotations": {
		"doctype": "Supplier Quotation",
		"fields": QUOTE_LIST_FIELDS,
		"date_field": "transaction_date",
		"tabs": {
			"Open": [["status", "in", REVISABLE_STATUSES]],
			"All": None,
			"Ordered": [["status", "in", ["Ordered", "Partially Ordered"]]],
			"Expired": [["status", "=", "Expired"]],
		},
		"search": ("name", "quotation_number"),
		"scope": lambda: _documents_scope("Supplier Quotation", _add_lost_quotations),
		"urgent": lambda: _expiring_quotations(),
		"deadline": "valid_till",
	},
	"orders": {
		"doctype": "Purchase Order",
		"fields": ORDER_LIST_FIELDS,
		"date_field": "transaction_date",
		"tabs": {
			"Active": [["status", "in", ACTIVE_ORDER_STATUSES]],
			"All": None,
			"Completed": [["status", "in", ["Completed", "Delivered"]]],
			"Closed": [["status", "=", "Closed"]],
		},
		"search": ("name",),
		"scope": lambda: _documents_scope("Purchase Order", _add_order_dates),
		# a line not all delivered and past its date
		"urgent": lambda: [["name", "in", _late_orders(_running_orders()) or [""]]],
		"deadline": "schedule_date",
	},
	"receipts": {
		"doctype": "Purchase Receipt",
		"fields": RECEIPT_LIST_FIELDS,
		"date_field": "posting_date",
		"tabs": {"All": None, "Received": [["is_return", "=", 0]], "Returned": [["is_return", "=", 1]]},
		"search": ("name", "supplier_delivery_note"),
		"scope": lambda: _documents_scope("Purchase Receipt"),
		# nothing on a receipt falls due
		"urgent": None,
		"deadline": None,
	},
	"invoices": {
		"doctype": "Purchase Invoice",
		"fields": INVOICE_LIST_FIELDS,
		"date_field": "posting_date",
		"tabs": {
			"Outstanding": [["outstanding_amount", ">", 0]],
			"All": None,
			"Overdue": [["status", "in", OVERDUE_INVOICE_STATUSES]],
			"Paid": [["status", "=", "Paid"]],
		},
		"search": ("name", "bill_no"),
		"scope": lambda: _documents_scope("Purchase Invoice", _add_last_payments),
		# unpaid and overdue: the buyer is late
		"urgent": lambda: [["outstanding_amount", ">", 0], ["status", "in", OVERDUE_INVOICE_STATUSES]],
		"deadline": "due_date",
	},
}


@frappe.whitelist()
def get_list_page(
	kind: str, tab: str = "All", search: str = "", start: int = 0, page_length: int = 0
) -> dict:
	"""One page of a list page, with how many documents match in all and in each tab. Urgent
	documents come first, soonest deadline first; the rest follow newest first."""
	config = LIST_PAGES.get(kind)
	if not config:
		frappe.throw(_("Unknown list: {0}").format(kind))
	if tab not in config["tabs"]:
		tab = "All"
	page_length = cint(page_length)
	if page_length not in LIST_PAGE_LENGTHS:
		page_length = LIST_PAGE_LENGTH

	scope, extra = config["scope"]()
	rows, total = _list_page(config, scope, extra, tab, search, start, page_length)
	return {
		"rows": rows,
		"total": total,
		"counts": {name: _count(config["doctype"], scope(value)) for name, value in config["tabs"].items()},
		**_sizes(page_length),
	}


def _list_page(config: dict, scope, extra, tab: str, search: str, start: int, page_length: int):
	"""The rows of one page of a tab, and how many documents match in all."""
	doctype = config["doctype"]
	conditions = scope(config["tabs"][tab])
	term = (search or "").strip()
	# matched as typed: % and _ are not wildcards here
	escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
	matching = [[field, "like", f"%{escaped}%"] for field in config["search"]] if term else None

	urgent = []
	if config["urgent"]:
		urgent = frappe.get_all(
			doctype,
			# an RFQ is urgent only while the supplier has still to quote it
			filters=conditions + scope(config.get("urgent_status")) + config["urgent"](),
			or_filters=matching,
			pluck="name",
			order_by=f"{config['deadline']} asc, creation desc",
		)
	rest = conditions + ([["name", "not in", urgent]] if urgent else [])

	start = max(cint(start), 0)
	names = urgent[start : start + page_length]
	wanted = page_length - len(names)
	if wanted:
		names += frappe.get_all(
			doctype,
			filters=rest,
			or_filters=matching,
			pluck="name",
			order_by=f"{config['date_field']} desc, creation desc",
			start=max(start - len(urgent), 0),
			limit=wanted,
		)

	return _list_rows(config, names, extra), len(urgent) + _count(doctype, rest, matching)


def _rfq_scope(invited: dict[str, str] | None = None):
	"""The RFQs the user's suppliers are invited to, by their quote status, and that status per row."""
	invited = _invited_rfqs() if invited is None else invited
	return (lambda status: _scope(invited, status)), (lambda rows: _rfq_row_extras(rows, invited))


def _rfq_row_extras(rows: list, invited: dict[str, str]) -> dict:
	"""Each row's quote status, and for an RFQ with no date of its own, the earliest date on its lines."""
	dates = _line_dates([row.name for row in rows if not row.schedule_date])
	return {
		row.name: {
			"quote_status": invited[row.name],
			**({"schedule_date": dates[row.name]} if row.name in dates else {}),
		}
		for row in rows
	}


def _line_dates(rfqs: list[str]) -> dict:
	"""The earliest date on each RFQ's lines: when the buyer needs the first of the goods."""
	if not rfqs:
		return {}
	line = frappe.qb.DocType("Request for Quotation Item")
	return dict(
		frappe.qb.from_(line)
		.select(line.parent, Min(line.schedule_date))
		.where(line.parent.isin(rfqs) & line.schedule_date.isnotnull())
		.groupby(line.parent)
		.run()
	)


def _documents_scope(doctype: str, extra=None):
	"""The user's suppliers' documents, narrowed by a tab's filters, and what `extra` adds to each row.
	A revised quotation is cancelled, so only its live revision shows."""
	scoped = _supplier_filters(doctype)
	return (lambda tab: scoped + list(tab or [])), (extra or (lambda rows: {}))


def _supplier_filters(doctype: str) -> list:
	"""Filters for the user's suppliers' submitted documents of this doctype. With no supplier, they
	match nothing rather than everything."""
	suppliers = get_parents_for_user("Supplier") or [""]
	return [
		[SUPPLIER_DOCTYPES[doctype], "in", suppliers],
		["docstatus", "=", 1],
		*SUPPLIER_EXTRA_FILTERS.get(doctype, []),
	]


def _replaced_by(doctype: str, name: str) -> dict | None:
	"""For an old link to one of the user's suppliers' documents that has since been cancelled and
	amended: the revision that took its place, for the page to open instead. Anything else is None."""
	field = SUPPLIER_DOCTYPES[doctype]
	suppliers = get_parents_for_user("Supplier") or [""]
	if not frappe.db.exists(doctype, [["name", "=", name], ["docstatus", "=", 2], [field, "in", suppliers]]):
		return None
	seen = {name}
	current = name
	while (
		current := frappe.db.get_value(doctype, {"amended_from": current}, "name")
	) and current not in seen:
		seen.add(current)
		# still this supplier's: a buyer can amend a document to another supplier
		if frappe.db.exists(doctype, [["name", "=", current], *_supplier_filters(doctype)]):
			return {"name": name, "replaced_by": current}
	return None


def _supplier_doc(doctype: str, name: str):
	"""One of the user's suppliers' submitted documents; anything else is not found."""
	if not frappe.db.exists(doctype, [["name", "=", name], *_supplier_filters(doctype)]):
		raise frappe.DoesNotExistError(_("{0} {1} not found").format(_(doctype), name))
	return frappe.get_doc(doctype, name)


def _add_lost_quotations(rows: list) -> dict:
	"""Which quotations the buyer ordered entirely from other suppliers: nothing is left for them to win."""
	return {name: {"ordered_elsewhere": "all"} for name in _lost_quotations([row.name for row in rows])}


def _expiring_quotations() -> list:
	"""Filters for the open quotations that stop being valid within a week, less the ones already lost
	to another supplier: their date no longer matters."""
	expiring = [
		["status", "in", REVISABLE_STATUSES],
		["valid_till", "between", [today(), add_days(today(), 7)]],
	]
	candidates = frappe.get_all(
		"Supplier Quotation", filters=[*_supplier_filters("Supplier Quotation"), *expiring], pluck="name"
	)
	lost = _lost_quotations(candidates)
	return [*expiring, *([["name", "not in", list(lost)]] if lost else [])]


def _lost_quotations(quotations: list[str]) -> set[str]:
	"""Of these quotations, those whose RFQ the buyer ordered entirely from other suppliers."""
	rfqs = _quotation_rfqs(quotations)
	if not rfqs:
		return set()
	suppliers = dict(
		frappe.get_all(
			"Supplier Quotation",
			filters={"name": ["in", list(rfqs)]},
			fields=["name", "supplier"],
			as_list=True,
		)
	)
	lost = _all_ordered_elsewhere({rfq: suppliers[name] for name, rfq in rfqs.items()})
	return {name for name, rfq in rfqs.items() if rfq in lost}


def _add_order_dates(rows: list) -> dict:
	"""When the buyer last received goods against each order, the date its note shows once delivered,
	and when its next delivery falls due."""
	added = _latest_dates(rows, "Purchase Receipt", "Purchase Receipt Item", "purchase_order", "last_receipt")
	for name, due in _next_due([row.name for row in rows]).items():
		added.setdefault(name, {})["next_due"] = due
	return added


def _running_orders() -> list:
	"""Filters for the user's suppliers' orders still to deliver."""
	return [
		*_supplier_filters("Purchase Order"),
		["status", "in", DELIVERING_ORDER_STATUSES],
		["per_received", "<", 100],
	]


def _next_due(orders: list[str]) -> dict:
	"""When each order's next delivery falls due: the earliest date of its lines not all received.
	ERPNext dates the order by its earliest line, delivered or not."""
	if not orders:
		return {}
	line = frappe.qb.DocType("Purchase Order Item")
	return dict(
		frappe.qb.from_(line)
		.select(line.parent, Min(line.schedule_date))
		.where(line.parent.isin(orders) & (line.received_qty < line.qty) & line.schedule_date.isnotnull())
		.groupby(line.parent)
		.run()
	)


def _late_orders(filters: list) -> list[str]:
	"""Of the orders these filters match, those with a line not all received and past its date. An
	order is dated by its earliest line, so only one past its own date can have such a line."""
	candidates = frappe.get_all(
		"Purchase Order", filters=[*filters, ["schedule_date", "<", today()]], pluck="name"
	)
	return [name for name, due in _next_due(candidates).items() if getdate(due) < getdate(today())]


def _add_last_payments(rows: list) -> dict:
	"""When each invoice was last paid: the date its note shows once paid."""
	latest = _latest_dates(
		rows, "Payment Entry", "Payment Entry Reference", "reference_name", "last_payment", "Purchase Invoice"
	)
	# paid on the invoice itself, as a cash purchase is: paid the day it was booked
	for name, date in frappe.get_all(
		"Purchase Invoice",
		filters={"name": ["in", [row.name for row in rows] or [""]], "is_paid": 1},
		fields=["name", "posting_date"],
		as_list=True,
	):
		before = latest.get(name, {}).get("last_payment")
		latest[name] = {"last_payment": max(filter(None, (before, date)))}
	return latest


def _latest_dates(
	rows: list, doctype: str, child: str, link: str, key: str, reference_doctype: str | None = None
) -> dict:
	names = [row.name for row in rows]
	if not names:
		return {}
	parent, line = frappe.qb.DocType(doctype), frappe.qb.DocType(child)
	query = (
		frappe.qb.from_(line)
		.inner_join(parent)
		.on(parent.name == line.parent)
		.select(line[link], Max(parent.posting_date))
		.where(line[link].isin(names) & (parent.docstatus == 1))
		.groupby(line[link])
	)
	if reference_doctype:
		query = query.where(line.reference_doctype == reference_doctype)
	else:
		# a return takes goods back: it is not a delivery
		query = query.where(parent.is_return == 0)
	return {name: {key: date} for name, date in query.run()}


def _invited_rfqs() -> dict[str, str]:
	"""The submitted RFQs the user's suppliers are invited to, each with its quote status.

	An RFQ has no supplier of its own: it belongs to every supplier on its `suppliers` table.
	When two of the user's suppliers are on one RFQ, it stays Pending until both have quoted."""
	suppliers = get_parents_for_user("Supplier")
	if not suppliers:
		return {}

	rows = frappe.get_all(
		"Request for Quotation Supplier",
		filters={"parenttype": "Request for Quotation", "supplier": ["in", suppliers]},
		fields=["parent", "supplier"],
	)
	quoted = _quoted(suppliers, list({row.parent for row in rows}))
	invited = {}
	supplier_for = {}
	for row in rows:
		if invited.get(row.parent) != "Pending":
			invited[row.parent] = "Received" if (row.supplier, row.parent) in quoted else "Pending"
			supplier_for[row.parent] = row.supplier

	# a draft is not the supplier's business, and a cancelled one is nobody's
	submitted = frappe.get_all(
		"Request for Quotation", filters={"name": ["in", list(invited)], "docstatus": 1}, pluck="name"
	)
	# every item already ordered from other suppliers, quoted or not: nothing is left to win, so it
	# leaves "To quote" and "Quoted". "Closed" is the portal's own word; ERPNext has only Pending
	# and Received here.
	for name in _all_ordered_elsewhere({name: supplier_for[name] for name in submitted}):
		invited[name] = "Closed"
	return {name: invited[name] for name in submitted}


def _all_ordered_elsewhere(pending: dict[str, str]) -> set[str]:
	"""Of these RFQs (each with the supplier invited to it), those whose every item the buyer
	already ordered in full from other suppliers. Two queries for the whole list, not two per RFQ."""
	return {
		rfq for rfq, (lines, taken, _touched) in _lines_ordered_elsewhere(pending).items() if lines <= taken
	}


def _lines_ordered_elsewhere(suppliers: dict[str, str]) -> dict[str, tuple[set, set, set]]:
	"""For each RFQ, with the supplier it is asked for: its lines, those the buyer already ordered in
	full from other suppliers, and those ordered from them at all. A line ordered in part is still
	open: counted in stock units, so an order in another unit adds up."""
	if not suppliers:
		return {}
	po, poi = frappe.qb.DocType("Purchase Order"), frappe.qb.DocType("Purchase Order Item")
	sqi = frappe.qb.DocType("Supplier Quotation Item")
	ordered: dict[tuple[str, str], float] = {}
	for rfq, line, winner, qty in (
		frappe.qb.from_(poi)
		.inner_join(po)
		.on(poi.parent == po.name)
		.inner_join(sqi)
		.on(poi.supplier_quotation_item == sqi.name)
		.select(sqi.request_for_quotation, sqi.request_for_quotation_item, po.supplier, poi.stock_qty)
		.where((po.docstatus == 1) & sqi.request_for_quotation.isin(list(suppliers)))
	).run():
		if winner != suppliers[rfq]:
			ordered[(rfq, line)] = ordered.get((rfq, line), 0) + flt(qty)
	if not ordered:
		return {}
	found: dict[str, tuple[set, set, set]] = {}
	for row in frappe.get_all(
		"Request for Quotation Item",
		filters={
			"parenttype": "Request for Quotation",
			"parent": ["in", list({rfq for rfq, _line in ordered})],
		},
		fields=["parent", "name", "qty", "stock_qty"],
	):
		lines, taken, touched = found.setdefault(row.parent, (set(), set(), set()))
		lines.add(row.name)
		got = ordered.get((row.parent, row.name), 0)
		if got > 0:
			touched.add(row.name)
		if got >= flt(row.stock_qty or row.qty):
			taken.add(row.name)
	return found


def _quoted(suppliers: list[str], rfqs: list[str]) -> set[tuple[str, str]]:
	"""(supplier, RFQ) pairs that already have a submitted quotation. Not a draft: one the buyer is
	still typing up in Desk is not the supplier's, and must not show to them.

	Not the RFQ row's `quote_status`: ERPNext keeps that Pending until every item is quoted,
	while a supplier can send only one quotation per RFQ, so after it there is nothing left to do."""
	if not rfqs:
		return set()
	query, sq, sqi = _quotations_query()
	return set(
		query.select(sq.supplier, sqi.request_for_quotation)
		.distinct()
		.where((sq.docstatus == 1) & sq.supplier.isin(suppliers) & sqi.request_for_quotation.isin(rfqs))
		.run()
	)


def _quotations_query():
	"""Supplier Quotations joined to their lines, which say the RFQ each line quotes for."""
	sq = frappe.qb.DocType("Supplier Quotation")
	sqi = frappe.qb.DocType("Supplier Quotation Item")
	return frappe.qb.from_(sqi).inner_join(sq).on(sqi.parent == sq.name), sq, sqi


def _scope(invited: dict[str, str], status: str | None) -> list:
	"""Filters for the invited RFQs with this quote status, or all of them."""
	names = [name for name, quote_status in invited.items() if status in (None, quote_status)]
	# `in` an empty list would match nothing anyway; spelled out so it never widens
	return [["name", "in", names or [""]]]


def _item_names(parenttype: str, parents: list[str]) -> dict[str, list[str]]:
	"""Item names per document, in their order on the document, from one query."""
	if not parents:
		return {}

	names: dict[str, list[str]] = {}
	for row in frappe.get_all(
		f"{parenttype} Item",
		filters={"parenttype": parenttype, "parent": ["in", parents]},
		fields=["parent", "item_name"],
		order_by="idx",
	):
		names.setdefault(row.parent, []).append(row.item_name)
	return names


def _public_file(url: str | None) -> str:
	"""The file's URL, or nothing when it is private: that would 403 for a website user."""
	url = url or ""
	return "" if url.startswith("/private/") else url


def _count(doctype: str, filters: list, or_filters: list | None = None) -> int:
	rows = frappe.get_all(doctype, filters=filters, or_filters=or_filters, fields=[{"COUNT": "*", "as": "n"}])
	return rows[0].n if rows else 0


def _sizes(page_length: int) -> dict:
	"""The page size used, and the ones the list's size buttons offer: the page draws them from here."""
	return {"page_length": page_length, "page_lengths": LIST_PAGE_LENGTHS}


def _list_rows(config: dict, names: list[str], extra) -> list[dict]:
	"""The list fields of these documents, in the order given, each with its item names and what
	its list adds (`extra`)."""
	if not names:
		return []
	found = {
		row.name: row
		for row in frappe.get_all(config["doctype"], filters={"name": ["in", names]}, fields=config["fields"])
	}
	rows = [found[name] for name in names if name in found]
	item_names = _item_names(config["doctype"], names)
	added = extra(rows)
	for row in rows:
		row["items"] = item_names.get(row.name, [])
		row.update(added.get(row.name, {}))
	return rows


@frappe.whitelist()
def get_rfq(name: str) -> dict:
	"""One RFQ the supplier is invited to, with their own quotation for it once they have sent one."""
	supplier, quote_status = _invited_supplier(name)
	rfq = frappe.get_doc("Request for Quotation", name)
	part_nos = _supplier_part_nos(supplier, [row.item_code for row in rfq.items])
	quotation = _supplier_quotation(supplier, name)

	return {
		**{field: rfq.get(field) for field in RFQ_FIELDS},
		"items": [
			{**row, "supplier_part_no": part_nos.get(row["item_code"])}
			for row in _item_rows(rfq, RFQ_ITEM_FIELDS)
		],
		"quote_status": quote_status,
		"currency": _quote_currency(supplier, rfq.company),
		"quotation": quotation,
		"ordered_elsewhere": _ordered_elsewhere(supplier, name, (quotation or {}).get("status")),
		# only yes or no: the draft itself is the buyer's, still being typed
		"buyer_drafting": not quotation and _buyer_drafting(supplier, name),
	}


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=10, seconds=60 * 60, user_based=True, ip_based=False)
def submit_rfq_quotation(
	name: str,
	items: list | str,
	valid_till: str | None = None,
	quotation_number: str | None = None,
	notes: str | None = None,
) -> str:
	"""Send the supplier's quote for an RFQ, submitted at once: it is their offer, and the buyer
	accepts it by ordering from it. Sent again before anything is ordered, it replaces the quote
	with a revision, the way ERPNext amends a document."""
	supplier, _quote_status = _invited_supplier(name)
	rfq = get_quotable_rfq(name, supplier)
	# ERPNext allows one live quotation per supplier and RFQ, so a revision takes the place of the old one
	previous = _revisable_quotation(supplier, rfq.name)
	if not previous:
		latest = _latest_quotation(supplier, rfq.name)
		if latest and _has_draft_order(latest):
			frappe.throw(_("The buyer is preparing an order from your quotation. Contact them to change it."))
		if _buyer_drafting(supplier, rfq.name):
			frappe.throw(
				_(
					"The buyer is already recording a quotation from you for this request. Contact them to change it."
				)
			)
		validate_existing_supplier_quotation(supplier, rfq.name)
		if _ordered_elsewhere(supplier, rfq.name) == "all":
			frappe.throw(_("The buyer has already ordered these items from another supplier."))

	if valid_till and getdate(valid_till) < getdate(today()):
		frappe.throw(_("Valid till cannot be in the past."))
	quotation = _build_quotation(rfq, supplier, frappe.parse_json(items))
	if not valid_till:
		frappe.throw(_("Enter the date this quotation is valid till."))
	quotation.update(
		{
			"valid_till": valid_till or None,
			"quotation_number": (quotation_number or "").strip()[:QUOTATION_NUMBER_LENGTH] or None,
			"terms": escape_html((notes or "").strip()).replace("\n", "<br>") or None,
			"amended_from": previous,
		}
	)

	sender = frappe.session.user
	with _as_administrator():
		if previous:
			frappe.get_doc("Supplier Quotation", previous).cancel()
		quotation.insert()
		quotation.submit()

	# saving elevated records Administrator as the owner and editor; the quote and its revision are
	# the supplier's
	frappe.db.set_value(
		"Supplier Quotation", quotation.name, {"owner": sender, "modified_by": sender}, update_modified=False
	)
	if previous:
		frappe.db.set_value("Supplier Quotation", previous, "modified_by", sender, update_modified=False)

	# whoever raised the RFQ, or is assigned to it, hears of the quote
	headline = _("{0} sent a revised quotation for {1}") if previous else _("{0} sent a quotation for {1}")
	notify_portal_response(
		"Supplier Quotation",
		quotation.name,
		headline.format(quotation.supplier_name or supplier, rfq.name),
		recipients=[rfq.owner, *frappe.parse_json(rfq.get("_assign") or "[]")],
	)
	return quotation.name


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=600, seconds=60 * 60, user_based=True, ip_based=False)
def preview_rfq_quotation(name: str, items: list | str) -> dict:
	"""What the quote being typed comes to, worked out as sending it would: the buyer's tax rule or
	default taxes, discount and rounding included. Nothing is saved."""
	supplier, _quote_status = _invited_supplier(name)
	quotation = _build_quotation(get_quotable_rfq(name, supplier), supplier, frappe.parse_json(items))
	return {**_pick(quotation, PREVIEW_FIELDS), "taxes": _taxes(quotation)}


# what the quote form's totals column needs from a preview
PREVIEW_FIELDS = (
	"currency",
	"total",
	"grand_total",
	"rounded_total",
	"rounding_adjustment",
	"discount_amount",
	"apply_discount_on",
)


def _build_quotation(rfq, supplier: str, items: list):
	"""The supplier's quote for an RFQ, filled in and totalled the way ERPNext does it, not yet saved."""
	rows = {row["name"]: row for row in _quoted_rows(rfq, items)}
	quotation = frappe.get_doc(
		{
			"doctype": "Supplier Quotation",
			"supplier": supplier,
			"company": rfq.company,
			"currency": _quote_currency(supplier, rfq.company),
			# the supplier's rate is final: a buying pricing rule must not change it, as in the old portal
			"ignore_pricing_rule": 1,
			"buying_price_list": frappe.db.get_value("Supplier", supplier, "default_price_list")
			or frappe.db.get_single_value("Buying Settings", "buying_price_list"),
		}
	)
	add_items(quotation, supplier, rfq, list(rows.values()))
	_apply_supplier_terms(quotation, rows)

	# Filling in the item details and taxes reads the Item, the supplier's payable Account and the
	# buyer's tax rules, which a supplier may not read, and must not: that would open them to every
	# supplier. The callers checked the supplier may quote, so only this runs elevated.
	with _as_administrator():
		quotation.run_method("set_missing_values")
		_apply_supplier_terms(quotation, rows)
		quotation.run_method("calculate_taxes_and_totals")
	return quotation


def _apply_supplier_terms(quotation, rows: dict[str, dict]) -> None:
	"""The supplier's own price, discount and delivery date on each line. Set again after the item
	details are filled in, since those may bring the price list's rate. The discount is ERPNext's
	own, so the line reads as list rate less a discount, as a desk user would enter it."""
	for item in quotation.items:
		row = rows[item.request_for_quotation_item]
		item.price_list_rate = row["rate"]
		item.discount_percentage = row["discount"]
		item.rate = flt(row["rate"] * (1 - row["discount"] / 100), item.precision("rate"))
		item.expected_delivery_date = row["delivery_date"]
		# what the comparison report ranks suppliers by
		item.lead_time_days = date_diff(row["delivery_date"], today()) if row["delivery_date"] else None


def _invited_supplier(rfq: str) -> tuple[str, str]:
	"""Which of the user's suppliers is invited to this submitted RFQ, with its quote status.
	One still to quote comes first. Anything else is not found, as if the RFQ did not exist."""
	suppliers = get_parents_for_user("Supplier")
	invited = []
	if suppliers and frappe.db.get_value("Request for Quotation", rfq, "docstatus") == 1:
		invited = frappe.get_all(
			"Request for Quotation Supplier",
			filters={"parenttype": "Request for Quotation", "parent": rfq, "supplier": ["in", suppliers]},
			pluck="supplier",
			order_by="idx",
		)
	if not invited:
		raise frappe.DoesNotExistError(_("Request for Quotation {0} not found").format(rfq))

	quoted = _quoted(invited, [rfq])
	supplier = next((s for s in invited if (s, rfq) not in quoted), invited[0])
	return supplier, "Received" if (supplier, rfq) in quoted else "Pending"


def _quoted_rows(rfq, items: list) -> list[dict]:
	"""The lines the supplier priced, checked. A line left without a rate is one they do not quote."""
	rfq_rows = {row.name: row for row in rfq.items}
	rows = []
	for item in items or []:
		row = rfq_rows.get(item.get("name"))
		if not row:
			frappe.throw(_("This item is not on Request for Quotation {0}.").format(rfq.name))
		rate, qty, discount = flt(item.get("rate")), flt(item.get("qty")), flt(item.get("discount"))
		if rate <= 0:
			continue
		if qty <= 0:
			frappe.throw(_("Row {0}: enter a quantity for {1}.").format(row.idx, row.item_name))
		if not 0 <= discount < 100:
			frappe.throw(_("Row {0}: the discount must be from 0 to 99%.").format(row.idx))
		delivery_date = item.get("delivery_date") or None
		if delivery_date and getdate(delivery_date) < getdate(today()):
			frappe.throw(_("Row {0}: the delivery date cannot be in the past.").format(row.idx))
		rows.append(
			{
				"name": row.name,
				"idx": row.idx,
				"qty": qty,
				"rate": rate,
				"discount": discount,
				"delivery_date": delivery_date,
			}
		)

	if not rows:
		frappe.throw(_("Enter a rate for at least one item."))
	return rows


def _supplier_quotation(supplier: str, rfq: str) -> dict | None:
	"""The supplier's latest submitted quotation for this RFQ, with its lines."""
	name = _latest_quotation(supplier, rfq)
	if not name:
		return None

	quotation = frappe.get_doc("Supplier Quotation", name)
	return {
		**_pick(quotation, (*QUOTE_FIELDS, "discount_amount", "apply_discount_on")),
		"items": [_pick(row, QUOTE_ITEM_FIELDS) for row in quotation.items],
		"taxes": _taxes(quotation),
		"has_draft_order": _has_draft_order(name),
	}


def _revisable_quotation(supplier: str, rfq: str) -> str | None:
	"""The supplier's quotation for this RFQ, while it can still be replaced: sent, and nothing ordered
	from it or from another supplier's."""
	name = _latest_quotation(supplier, rfq)
	if not name:
		return None
	docstatus, status = frappe.db.get_value("Supplier Quotation", name, ["docstatus", "status"])
	if docstatus != 1 or status not in REVISABLE_STATUSES or _has_draft_order(name):
		return None
	# the buyer ordered everything from other suppliers: there is nothing left to win
	return None if _ordered_elsewhere(supplier, rfq, status) == "all" else name


def _has_draft_order(quotation: str) -> bool:
	"""Whether the buyer has a draft purchase order from this quotation. Revising would cancel the
	quotation, and ERPNext then refuses to submit that order."""
	return bool(frappe.db.exists("Purchase Order Item", {"supplier_quotation": quotation, "docstatus": 0}))


def _buyer_drafting(supplier: str, rfq: str) -> bool:
	"""Whether a draft quotation from this supplier for this RFQ is being typed up in Desk, as a buyer
	does with a quote that came by email. ERPNext then refuses another quotation from the supplier."""
	query, sq, sqi = _quotations_query()
	return bool(
		query.select(sq.name)
		.where((sq.docstatus == 0) & (sq.supplier == supplier) & (sqi.request_for_quotation == rfq))
		.limit(1)
		.run()
	)


def _latest_quotation(supplier: str, rfq: str) -> str | None:
	"""The supplier's newest submitted quotation for this RFQ. A draft is the buyer's, still being typed."""
	query, sq, sqi = _quotations_query()
	found = (
		query.select(sq.name)
		.where((sq.docstatus == 1) & (sq.supplier == supplier) & (sqi.request_for_quotation == rfq))
		.orderby(sq.creation, order=frappe.qb.desc)
		.limit(1)
		.run(pluck=True)
	)
	return found[0] if found else None


def _ordered_elsewhere(supplier: str, rfq: str, own_status: str | None = None) -> str:
	"""How much of this RFQ the buyer ordered from other suppliers: "all" of its items, in full,
	"some", or "". Only that: who won, and at what price, is not this supplier's business. Nothing is
	said once the supplier's own quote has been ordered from: its own status tells them what they need."""
	if own_status in ("Ordered", "Partially Ordered"):
		return ""
	lines, taken, touched = _lines_ordered_elsewhere({rfq: supplier}).get(rfq, (set(), set(), set()))
	if lines and lines <= taken:
		return "all"
	return "some" if touched else ""


def _supplier_part_nos(supplier: str, item_codes: list[str]) -> dict[str, str]:
	"""The supplier's own part number for each item, from the Item's Supplier Items table."""
	if not item_codes:
		return {}
	return {
		row.parent: row.supplier_part_no
		for row in frappe.get_all(
			"Item Supplier",
			filters={"parenttype": "Item", "parent": ["in", item_codes], "supplier": supplier},
			fields=["parent", "supplier_part_no"],
		)
		if row.supplier_part_no
	}


def _quote_currency(supplier: str, company: str) -> str:
	"""The supplier's own currency, else the company's: the rule the old portal page used."""
	return frappe.db.get_value("Supplier", supplier, "default_currency") or frappe.get_cached_value(
		"Company", company, "default_currency"
	)


@contextmanager
def _as_administrator():
	"""Run the block as Administrator, then hand the session back. Frappe's web forms switch users
	the same way: only `frappe.session.user`, since `frappe.set_user` would also reset the session
	id and the request's form data."""
	user = frappe.session.user
	frappe.session.user = "Administrator"
	try:
		yield
	finally:
		frappe.session.user = user


@frappe.whitelist()
def get_quotation(name: str) -> dict:
	"""One of the user's suppliers' sent quotations: its lines, the RFQ it answers, and the orders
	placed from it."""
	if replaced := _replaced_by("Supplier Quotation", name):
		return replaced
	quotation = _supplier_doc("Supplier Quotation", name)
	rfq = _quotation_rfqs([name]).get(name)
	reply = {field: quotation.get(field) for field in QUOTE_PAGE_FIELDS}
	return {
		**reply,
		# a quotation has no print of its own here: its photos follow the RFQ it answers, so the
		# supplier sees the same items on the RFQ, the quotation and the order
		"items": _item_rows(
			quotation,
			("item_code", "item_name", "description", "uom", *QUOTE_ITEM_FIELDS),
			photos_as="Request for Quotation" if rfq else None,
		),
		"taxes": _taxes(quotation),
		"rfq": rfq,
		"orders": sorted(
			set(
				frappe.get_all(
					"Purchase Order Item",
					filters={"supplier_quotation": name, "docstatus": 1},
					pluck="parent",
				)
			)
		),
		"ordered_elsewhere": _ordered_elsewhere(quotation.supplier, rfq, reply["status"]) if rfq else "",
		"has_draft_order": _has_draft_order(name),
	}


def _quotation_rfqs(quotations: list[str]) -> dict[str, str]:
	"""The RFQ each quotation answers, from its lines. A quotation made without one has none."""
	if not quotations:
		return {}
	rows = frappe.get_all(
		"Supplier Quotation Item",
		filters={"parent": ["in", quotations], "request_for_quotation": ["is", "set"]},
		fields=["parent", "request_for_quotation"],
		order_by="idx",
	)
	found = {}
	for row in rows:
		found.setdefault(row.parent, row.request_for_quotation)
	return found


@frappe.whitelist()
def get_order(name: str) -> dict:
	"""One of the supplier's purchase orders, with only what its page shows, and the receipts and
	invoices booked against it."""
	if replaced := _replaced_by("Purchase Order", name):
		return replaced
	order = _supplier_doc("Purchase Order", name)
	return {
		**_reply(order, ORDER_FIELDS, ORDER_ITEM_FIELDS),
		"quotation_numbers": _quotation_numbers(order),
		"next_due": _next_due([name]).get(name),
		"receipts": _booked_against(name, "Purchase Receipt"),
		"invoices": _booked_against(name, "Purchase Invoice"),
	}


def _booked_against(order: str, doctype: str) -> list[str]:
	"""The user's suppliers' submitted receipts or invoices with a line for this order."""
	return sorted(
		set(
			frappe.get_all(
				doctype,
				filters=[*_supplier_filters(doctype), [f"{doctype} Item", "purchase_order", "=", order]],
				pluck="name",
			)
		)
	)


def _quotation_numbers(order) -> dict[str, str]:
	"""The supplier's own number for each of their quotations this order was made from: the
	reference they know it by. ERPNext does not copy it onto the order."""
	quotations = {row.supplier_quotation for row in order.items if row.supplier_quotation}
	if not quotations:
		return {}
	return dict(
		frappe.get_all(
			"Supplier Quotation",
			filters=[
				["name", "in", list(quotations)],
				["quotation_number", "is", "set"],
				*_supplier_filters("Supplier Quotation"),
			],
			fields=["name", "quotation_number"],
			as_list=True,
		)
	)


@frappe.whitelist()
def get_receipt(name: str) -> dict:
	"""One of the supplier's purchase receipts, with the order lines it receives against."""
	if replaced := _replaced_by("Purchase Receipt", name):
		return replaced
	receipt = _supplier_doc("Purchase Receipt", name)
	return {
		**_pick(receipt, RECEIPT_FIELDS),
		"items": [_pick(row, RECEIPT_ITEM_FIELDS) for row in receipt.items],
		"order_lines": _order_lines(receipt),
	}


@frappe.whitelist()
def get_invoice(name: str) -> dict:
	"""One of the supplier's purchase invoices, with only what its page shows, and its payments."""
	if replaced := _replaced_by("Purchase Invoice", name):
		return replaced
	invoice = _supplier_doc("Purchase Invoice", name)
	return {
		**_reply(invoice, INVOICE_FIELDS, INVOICE_ITEM_FIELDS),
		"payments": _payments(invoice),
		"party_total": get_total_in_party_account_currency(invoice),
		"debited": 0 if invoice.is_return else _debited(invoice.name),
	}


def _reply(doc, fields: tuple[str, ...], item_fields: tuple[str, ...]) -> dict:
	return {
		**_pick(doc, fields),
		"items": _item_rows(doc, item_fields),
		"taxes": _taxes(doc),
	}


def _print_shows_item_images(doctype: str) -> bool:
	"""Whether the doctype's default print format has a photo on its item lines. A hand-written
	HTML format cannot be read, so it counts as no photos."""
	try:
		for _where, zone in iter_zones(_default_print_layout(doctype)):
			for df in iter_fields(zone):
				if df.get("fieldname") == "items":
					return any(_column_shows(column, "image") for column in df.get("table_columns") or [])
	except Exception:
		# the layout is whatever someone saved; a broken one costs the photos, not the customer's page
		pass
	return False


def _default_print_layout(doctype: str) -> dict:
	"""The default print format's builder layout, older layouts converted, or {} when there is none."""
	print_format = frappe.get_meta(doctype).default_print_format
	if not print_format:
		return {}
	readable = {"name": print_format, "disabled": 0, "custom_format": 0}
	layout = frappe.parse_json(frappe.db.get_value("Print Format", readable, "format_data") or "{}")
	if isinstance(layout, list):
		layout, _dropped = convert_classic_to_beta(layout, frappe.get_meta(doctype))
	return layout if isinstance(layout, dict) else {}


def _column_shows(column: dict, fieldname: str) -> bool:
	"""Whether a print table column shows the field, as its own value or merged under another."""
	merged = column.get("merged_fields") or []
	return column.get("fieldname") == fieldname or any(f.get("fieldname") == fieldname for f in merged)


def _item_rows(doc, fields: tuple[str, ...], photos_as: str | None = None) -> list[dict]:
	"""The document's lines, each with its photo when the default print format shows photos, as the
	customer portal does: the page then matches what Print gives. `photos_as` follows another
	doctype's print instead. A private photo stays private."""
	show = _print_shows_item_images(photos_as or doc.doctype)
	return [
		{**_pick(row, fields), "image": _public_file(row.get("image")) if show else ""} for row in doc.items
	]


def _taxes(doc) -> list[dict]:
	"""The document's tax lines; a deducted tax lowers the total, so it is sent as a negative amount."""
	return [
		{
			**_pick(row, TAX_FIELDS),
			"tax_amount": -row.tax_amount if row.add_deduct_tax == "Deduct" else row.tax_amount,
		}
		for row in doc.taxes
	]


def _pick(doc, fields: tuple[str, ...]) -> dict:
	return {field: doc.get(field) for field in fields}


def _order_lines(receipt) -> list[dict]:
	"""Every line of the orders a receipt receives against, for its "Yet to deliver" column."""
	orders = sorted({row.purchase_order for row in receipt.items if row.purchase_order})
	if not orders:
		return []
	visible = frappe.get_all(
		"Purchase Order", filters=[["name", "in", orders], *_supplier_filters("Purchase Order")], pluck="name"
	)
	if not visible:
		return []
	return frappe.get_all(
		"Purchase Order Item",
		filters={"parenttype": "Purchase Order", "parent": ["in", visible]},
		fields=["parent as purchase_order", "item_code", "qty", "received_qty", "uom"],
	)


def _payments(invoice) -> list[dict]:
	"""What the buyer has paid against one invoice, oldest first."""
	# paid on the invoice itself, as a cash purchase is, with no payment entry of its own
	on_invoice = (
		[
			{
				"name": invoice.name,
				"posting_date": invoice.posting_date,
				"mode_of_payment": invoice.mode_of_payment,
				"reference_no": None,
				"allocated_amount": invoice.paid_amount,
			}
		]
		if invoice.is_paid and invoice.paid_amount
		else []
	)
	allocations = frappe.get_all(
		"Payment Entry Reference",
		filters={
			"parenttype": "Payment Entry",
			"reference_doctype": "Purchase Invoice",
			"reference_name": invoice.name,
		},
		fields=["parent", "allocated_amount"],
	)
	if not allocations:
		return on_invoice
	entries = {
		entry.name: entry
		for entry in frappe.get_all(
			"Payment Entry",
			filters=[
				["name", "in", [row.parent for row in allocations]],
				*_supplier_filters("Payment Entry"),
			],
			fields=["name", "posting_date", "mode_of_payment", "reference_no"],
		)
	}
	# a payment split over the invoice's payment terms has one reference row per term: one payment
	allocated = {}
	for row in allocations:
		if row.parent in entries:
			allocated[row.parent] = allocated.get(row.parent, 0) + row.allocated_amount
	payments = [{**entries[name], "allocated_amount": amount} for name, amount in allocated.items()]
	return sorted(on_invoice + payments, key=lambda payment: (payment["posting_date"], payment["name"]))


def _debited(invoice: str) -> float:
	"""What the supplier's debit notes against one invoice took off what it owes, a positive amount."""
	notes = frappe.get_all(
		"Purchase Invoice",
		# one that keeps its own outstanding leaves this invoice's balance alone
		filters={"return_against": invoice, "is_return": 1, "docstatus": 1, "update_outstanding_for_self": 0},
		pluck="name",
	)
	return -sum(
		get_total_in_party_account_currency(frappe.get_doc("Purchase Invoice", note)) for note in notes
	)


# the documents a supplier can talk about with the buyer, from the portal
COMMENT_DOCTYPES = ("Supplier Quotation", "Purchase Order", "Purchase Receipt", "Purchase Invoice")


@frappe.whitelist()
def get_portal_comments(doctype: str, name: str) -> list[dict]:
	"""The conversation the supplier can see on one of their documents: published comments, newest
	first, as Desk's timeline lists them."""
	_commentable(doctype, name)
	comments = frappe.get_all(
		"Comment",
		filters={
			"reference_doctype": doctype,
			# a revision cancels the document it replaces; the conversation on that one carries on here
			"reference_name": ["in", [name, *_earlier_revisions(doctype, name)]],
			"comment_type": "Comment",
			"published": 1,
		},
		fields=["name", "comment_by", "comment_email", "content", "creation"],
		order_by="creation desc",
	)
	for comment in comments:
		# a staff member's login email is theirs to give out; the name is enough to show
		if comment.comment_email != frappe.session.user:
			comment.comment_email = ""
		comment["attachments"] = []
		# lets a page tell this thread from the one it showed before, whichever revision it was left on
		comment["thread"] = name
	return comments


def _earlier_revisions(doctype: str, name: str) -> list[str]:
	"""The documents this one revises, newest first, while they were the same supplier's: a buyer can
	amend a document to another supplier, and the conversation before that is not this one's."""
	field = SUPPLIER_DOCTYPES[doctype]
	supplier, name = frappe.db.get_value(doctype, name, [field, "amended_from"]) or (None, None)
	earlier = []
	while name and name not in earlier:
		before, previous = frappe.db.get_value(doctype, name, [field, "amended_from"]) or (None, None)
		if before != supplier:
			break
		earlier.append(name)
		name = previous
	return earlier


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=30, seconds=60 * 60, user_based=True, ip_based=False)
def add_portal_comment(doctype: str, name: str, content: str) -> dict:
	"""Post a published comment as the signed-in supplier, which the buyer sees on the document's timeline."""
	_commentable(doctype, name)
	# Comment.validate cleans the HTML too; this copy only tells an empty message apart
	content = sanitize_html((content or "").strip())
	if not content:
		frappe.throw(_("Write something first"))

	comment = frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Comment",
			"reference_doctype": doctype,
			"reference_name": name,
			"comment_email": frappe.session.user,
			"comment_by": frappe.utils.get_fullname(frappe.session.user),
			"published": 1,
			"content": content,
		}
	).insert(ignore_permissions=True)

	notify_portal_response(
		doctype,
		name,
		_("{0} commented on {1}").format(comment.comment_by, name),
		content,
		recipients=_buyer_side(doctype, name),
	)
	return {"name": comment.name}


def _buyer_side(doctype: str, name: str) -> list[str]:
	"""Who on the buyer's side hears of the supplier's comment: whoever owns the document or is
	assigned to it. The supplier owns their own quotation, so for one that is the RFQ's people."""
	docs = [(doctype, name)]
	if doctype == "Supplier Quotation":
		rfq = _quotation_rfqs([name]).get(name)
		docs = [(doctype, name), *([("Request for Quotation", rfq)] if rfq else [])]
	people = []
	for dt, dn in docs:
		owner, assigned = frappe.db.get_value(dt, dn, ["owner", "_assign"])
		people += [owner, *frappe.parse_json(assigned or "[]")]
	# the supplier's own people are not the buyer's side
	suppliers = set(get_portal_users_for_document(doctype, name))
	return [person for person in people if person not in suppliers]


def get_portal_users_for_document(doctype: str, name: str) -> list[str]:
	"""Portal users of the supplier a document belongs to. A User's name is its email."""
	if doctype not in COMMENT_DOCTYPES:
		return []
	supplier = frappe.db.get_value(doctype, name, SUPPLIER_DOCTYPES[doctype])
	if not supplier:
		return []
	return frappe.get_all("Portal User", filters={"parenttype": "Supplier", "parent": supplier}, pluck="user")


def protect_supplier_comment(doc, method: str | None = None) -> None:
	"""A supplier's own words are not the buyer's team to rewrite: Desk lets a System Manager edit
	any comment, but one written from the portal is the supplier's statement, so only they may."""
	if doc.comment_type != "Comment":
		return
	before = doc.get_doc_before_save()
	if not before or before.content == doc.content or doc.owner == frappe.session.user:
		return
	if doc.owner not in get_portal_users_for_document(doc.reference_doctype, doc.reference_name):
		return
	frappe.throw(
		_("This comment was written by the supplier and can only be edited by them."), frappe.PermissionError
	)


def notify_portal_response(
	doctype: str, name: str, headline: str, body: str = "", recipients: list[str] | None = None
) -> None:
	"""Bell notification, by default for whoever owns the document plus anyone assigned to it."""
	from frappe.desk.doctype.notification_log.notification_log import make_notification_logs

	if recipients is None:
		owner = frappe.db.get_value(doctype, name, "owner")
		assigned = frappe.parse_json(frappe.db.get_value(doctype, name, "_assign") or "[]")
		recipients = [owner, *assigned]

	recipients = {u for u in recipients if u and u not in (frappe.session.user, "Guest")}
	if not recipients:
		return

	recipients = frappe.db.get_values(
		"User", {"name": ("in", list(recipients)), "enabled": 1}, "email", pluck=True
	)
	if not recipients:
		return

	make_notification_logs(
		frappe._dict(
			{
				"type": "Alert",
				"subject": headline,
				"email_content": body or headline,
				"document_type": doctype,
				"document_name": name,
				"from_user": frappe.session.user,
			}
		),
		list(recipients),
	)


def notify_supplier_of_comment(doc, method: str | None = None) -> None:
	"""Tell the supplier when the buyer's comment on one of their documents becomes visible to them."""
	if doc.comment_type != "Comment" or not doc.published or doc.reference_doctype not in COMMENT_DOCTYPES:
		return
	# only a document the supplier can open: a draft or a cancelled one would land on "not found"
	if frappe.db.get_value(doc.reference_doctype, doc.reference_name, "docstatus") != 1:
		return
	# on_update fires on every save, the one right after insert included; only a 0 -> 1 publish is news
	if method == "on_update":
		before = doc.get_doc_before_save()
		if not before or before.published == doc.published:
			return

	recipients = get_portal_users_for_document(doc.reference_doctype, doc.reference_name)
	# the supplier's own comments already happened in front of them
	if not recipients or doc.owner in recipients:
		return
	notify_portal_response(
		doc.reference_doctype,
		doc.reference_name,
		_("New comment on {0}").format(doc.reference_name),
		doc.content or "",
		recipients=recipients,
	)


def _commentable(doctype: str, name: str) -> None:
	"""Only a document the supplier may open; anything else is not found."""
	if doctype not in COMMENT_DOCTYPES:
		raise frappe.DoesNotExistError
	_supplier_doc(doctype, name)


# ---------------------------------------------------------------- home
# how many rows each list shows on home; "Show all" opens the list itself
HOME_ROWS = 3


@frappe.whitelist()
def get_home() -> dict:
	"""What needs the supplier, and the first rows of each list as the list itself orders them:
	urgent first, then newest."""
	invited = _invited_rfqs()
	lists = {}
	for kind in ("rfqs", "orders", "invoices"):
		config = LIST_PAGES[kind]
		scope, extra = _rfq_scope(invited) if kind == "rfqs" else config["scope"]()
		rows, total = _list_page(config, scope, extra, "All", "", 0, HOME_ROWS)
		lists[kind] = {"rows": rows, "total": total}
	return {
		**lists,
		"summary": _home_summary(invited),
		# the heading: the supplier the user acts for, as the buyer has them on record
		"supplier_name": ", ".join(
			frappe.get_all(
				"Supplier",
				filters={"name": ["in", get_parents_for_user("Supplier") or [""]]},
				pluck="supplier_name",
			)
		),
	}


def _home_summary(invited: dict[str, str]) -> dict:
	"""Home's figures, counted in the database."""
	to_quote = [name for name, status in invited.items() if status == "Pending"]
	# by the RFQ's own date, or else its lines' earliest: an RFQ without either is not late
	header = dict(
		frappe.get_all(
			"Request for Quotation",
			filters={"name": ["in", to_quote or [""]]},
			fields=["name", "schedule_date"],
			as_list=True,
		)
	)
	lines = _line_dates([name for name, date in header.items() if not date])
	needed = list(filter(None, (date or lines.get(name) for name, date in header.items())))
	running = frappe.get_all("Purchase Order", filters=_running_orders(), pluck="name")
	# by the lines still to deliver: ERPNext dates an order by its earliest line, delivered or not
	due = list(_next_due(running).values())
	unpaid = [*_supplier_filters("Purchase Invoice"), ["outstanding_amount", ">", 0]]
	return {
		"rfqs": {
			"count": len(to_quote),
			"next_needed": min(needed, default=None),
			# an RFQ stays open after its date: the earliest one is then in the past, not "next"
			"late": sum(getdate(date) < getdate(today()) for date in needed),
		},
		"orders": {
			"count": len(running),
			"next_delivery": min(due, default=None),
			"late": sum(getdate(date) < getdate(today()) for date in due),
		},
		"invoices": {
			**_aggregate("Purchase Invoice", unpaid, {"count": ("COUNT", "*")}),
			"overdue": _aggregate(
				"Purchase Invoice",
				[*unpaid, ["status", "in", OVERDUE_INVOICE_STATUSES]],
				{"count": ("COUNT", "*")},
			)["count"],
			# per currency: an invoice keeps what is owed in its party account's, and two cannot be added
			"owed": frappe.get_all(
				"Purchase Invoice",
				filters=unpaid,
				fields=["party_account_currency as currency", {"SUM": "outstanding_amount", "as": "amount"}],
				group_by="party_account_currency",
				order_by="amount desc",
			),
		},
	}


def _aggregate(doctype: str, filters: list, columns: dict[str, tuple[str, str]]) -> dict:
	"""One row of aggregates, as {name: value}: a count of nothing is 0, a date of nothing None."""
	fields = [{function: column, "as": name} for name, (function, column) in columns.items()]
	row = frappe.get_all(doctype, filters=filters, fields=fields)[0]
	return {
		name: row.get(name) or (0 if function in ("COUNT", "SUM") else None)
		for name, (function, _column) in columns.items()
	}


def get_website_user_home_page(user: str) -> str | None:
	"""A supplier who logs in, or sets their password from the invite, lands on the new portal."""
	if frappe.db.get_value("User", user, "user_type") != "Website User":
		return None
	return "supplier-portal" if "Supplier" in frappe.get_roles(user) else None


def get_portal_boot() -> dict:
	"""The language and the number and currency formats, as Desk reads them, for the portal's first render."""
	return {
		"lang": frappe.local.lang,
		"translations_version": get_translation_version(),
		"currency": frappe.db.get_default("currency"),
		"number_format": frappe.db.get_default("number_format"),
		"currency_precision": frappe.db.get_default("currency_precision"),
		"hide_currency_symbol": frappe.db.get_default("hide_currency_symbol") in ("1", "Yes"),
		"currencies": {
			currency.pop("name"): currency
			for currency in frappe.get_all(
				"Currency",
				filters={"enabled": 1},
				fields=["name", "symbol", "symbol_on_right", "number_format"],
			)
		},
	}


@frappe.whitelist()
def get_portal_context() -> dict:
	"""Who the signed-in portal user is, and which suppliers they may see."""
	user = frappe.session.user
	full_name, email = frappe.db.get_value("User", user, ["full_name", "email"]) or (None, None)
	suppliers = get_parents_for_user("Supplier")

	return {
		"user": user,
		"full_name": full_name,
		"email": email,
		"suppliers": suppliers,
		# the names the sidebar shows; a supplier's ID can be a naming series
		"supplier_names": frappe.get_all(
			"Supplier",
			filters={"name": ["in", suppliers or [""]]},
			pluck="supplier_name",
			order_by="supplier_name",
		),
		"company": _portal_company(),
	}


def _portal_company() -> dict:
	"""The company the portal is branded as: the one the supplier does business with, by their latest
	invoice, else order, else quotation, as the customer portal does; else their latest RFQ, which
	any company may send; else the site default."""
	company = None
	for doctype in ("Purchase Invoice", "Purchase Order", "Supplier Quotation"):
		company = frappe.db.get_value(
			doctype, _supplier_filters(doctype), "company", order_by="creation desc"
		)
		if company:
			break

	invited = None if company else _invited_rfqs()
	if invited:
		company = frappe.db.get_value(
			"Request for Quotation", {"name": ["in", list(invited)]}, "company", order_by="creation desc"
		)

	company = company or frappe.defaults.get_global_default("company")
	if not company:
		return {"name": "", "logo": ""}

	return {"name": company, "logo": _public_file(frappe.db.get_value("Company", company, "company_logo"))}
