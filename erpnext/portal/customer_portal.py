# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""The customer portal's server side: what its pages read, and the few things a customer
can do there (answer a quotation, comment, keep an address book). Each endpoint chooses its
own fields, so a customer receives what their page shows and nothing else."""

import re

import frappe
from frappe import _
from frappe.printing.doctype.print_format.classic_converter import convert_classic_to_beta
from frappe.printing.layout import iter_fields, iter_zones
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Max
from frappe.rate_limiter import rate_limit
from frappe.translate import get_translation_version
from frappe.utils import add_days, cint, getdate, today
from frappe.utils.caching import request_cache
from frappe.utils.html_utils import sanitize_html

from erpnext.accounts.doctype.sales_invoice.services.status import get_total_in_party_account_currency
from erpnext.controllers.website_list_for_contact import get_parents_for_user

PORTAL_DOCTYPES = {
	"Quotation": "party_name",
	"Sales Order": "customer",
	"Sales Invoice": "customer",
	"Delivery Note": "customer",
	"Payment Entry": "party",
}

PORTAL_EXTRA_FILTERS = {
	"Quotation": {"quotation_to": "Customer"},
	"Payment Entry": {"party_type": "Customer"},
}


def _portal_customers() -> list[str]:
	"""The customers the signed-in user acts for. Every portal check asks, so it is read once per request."""
	return _customers_of(frappe.session.user)


@request_cache
def _customers_of(user: str) -> list[str]:
	# `user` is only the cache key: a test or a job can switch users within one request
	return get_parents_for_user("Customer")


def _portal_filters(doctype: str, filters: dict | None = None) -> dict | None:
	"""The caller's filters with the scope forced on top, or None when the user is linked to no customer."""
	if doctype not in PORTAL_DOCTYPES:
		frappe.throw(_("{0} is not available on the portal").format(doctype), frappe.PermissionError)

	customers = _portal_customers()
	if not customers:
		return None

	# applied last: a caller cannot widen the scope by passing its own value
	filters = dict(filters or {})
	filters.update(PORTAL_EXTRA_FILTERS.get(doctype, {}))
	filters[PORTAL_DOCTYPES[doctype]] = ["in", customers]
	# a draft is not the customer's business, and a cancelled one is nobody's
	filters["docstatus"] = 1
	return filters


LIST_LIMIT = 200

ITEM_FIELDS = ("item_code", "item_name", "description", "qty", "uom", "rate", "amount")

# the print format leaves out a tax already inside the rate, so the portal does too
TAX_FIELDS = ("description", "tax_amount", "included_in_print_rate")

QUOTATION_LIST_FIELDS = (
	"name",
	"status",
	"transaction_date",
	"valid_till",
	"grand_total",
	"rounded_total",
	"currency",
	"amended_from",
	"revision_of",
	"is_active",
	"portal_response",
	"company",
	"customer_name",
	"party_name",
)

QUOTATION_FIELDS = (
	"name",
	"status",
	"transaction_date",
	"valid_till",
	"amended_from",
	"revision_of",
	"is_active",
	"company",
	"customer_name",
	"party_name",
	"currency",
	"total",
	"grand_total",
	"rounded_total",
	"rounding_adjustment",
	"discount_amount",
	"apply_discount_on",
	"in_words",
	"terms",
	"contact_display",
	"contact_person",
	"contact_email",
	"contact_mobile",
	"address_display",
	"shipping_address",
	"portal_response",
)

ORDER_LIST_FIELDS = (
	"name",
	"status",
	"transaction_date",
	"delivery_date",
	"per_delivered",
	"grand_total",
	"rounded_total",
	"currency",
	"company",
	"customer_name",
	"customer",
)

ORDER_FIELDS = (
	"name",
	"status",
	"transaction_date",
	"delivery_date",
	"per_delivered",
	"per_billed",
	"po_no",
	"company",
	"customer_name",
	"customer",
	"currency",
	"total",
	"grand_total",
	"rounded_total",
	"rounding_adjustment",
	"discount_amount",
	"apply_discount_on",
	"in_words",
	"terms",
	"contact_display",
	"contact_person",
	"contact_email",
	"contact_mobile",
	"contact_phone",
	"address_display",
	"shipping_address",
)

# the quotation each line came from, for the order page's "From quotation" link
ORDER_ITEM_FIELDS = (*ITEM_FIELDS, "prevdoc_docname", "delivered_qty")

INVOICE_LIST_FIELDS = (
	"name",
	"status",
	"posting_date",
	"due_date",
	"outstanding_amount",
	"is_return",
	"grand_total",
	"rounded_total",
	"currency",
	"company",
	"customer_name",
	"customer",
)

INVOICE_FIELDS = (
	"name",
	"status",
	"posting_date",
	"due_date",
	"outstanding_amount",
	"is_return",
	# a credit note names the invoice it corrects
	"return_against",
	"company",
	"customer_name",
	"customer",
	"customer_gstin",
	"currency",
	# outstanding and payments are kept in this one, which can differ from the invoice's
	"party_account_currency",
	"total",
	"grand_total",
	"rounded_total",
	"rounding_adjustment",
	"discount_amount",
	"apply_discount_on",
	"in_words",
	"terms",
	"contact_display",
	"contact_person",
	"contact_email",
	"contact_mobile",
	"address_display",
	"shipping_address",
)

# the order each line came from, for the invoice page's "From order" link
INVOICE_ITEM_FIELDS = (*ITEM_FIELDS, "sales_order")

SHIPMENT_LIST_FIELDS = (
	"name",
	"posting_date",
	"is_return",
	"total_qty",
	"company",
	"customer_name",
	"customer",
)

SHIPMENT_FIELDS = (
	"name",
	"posting_date",
	"is_return",
	"company",
	"customer_name",
	"customer",
	"currency",
	"grand_total",
	"rounded_total",
	"terms",
	"po_no",
	"total_qty",
	"per_billed",
	"contact_display",
	"contact_person",
	"contact_email",
	"contact_mobile",
	"lr_no",
	"transporter_name",
	"vehicle_no",
	"driver_name",
	"address_display",
	"shipping_address",
)

# a shipment page shows quantities, not prices, and links each line to its order
SHIPMENT_ITEM_FIELDS = ("item_code", "item_name", "description", "qty", "uom", "against_sales_order")

# the page sizes a customer can pick under a list; the first is the default
LIST_PAGE_LENGTHS = (20, 50, 100)
LIST_PAGE_LENGTH = LIST_PAGE_LENGTHS[0]

# Sales Order statuses where the order is still running; the pages keep the same list
ACTIVE_ORDER_STATUSES = ("To Deliver and Bill", "To Deliver", "To Bill", "To Pay", "On Hold")

# ERPNext marks an invoice overdue once any instalment is late; `due_date` is only the last one's
OVERDUE_INVOICE_STATUSES = ("Overdue", "Overdue and Discounted")

# Each list page: its tabs, what its search looks at, and which documents float to the top
# (by `deadline`, soonest first) before the rest, newest first.
LIST_PAGES = {
	"quotations": {
		"doctype": "Quotation",
		"fields": QUOTATION_LIST_FIELDS,
		"date_field": "transaction_date",
		"filters": {"status": ["!=", "Replied"]},
		"tabs": {
			# an older version replaced by a revision cannot be ordered any more
			"Open": [["status", "=", "Open"], ["is_active", "=", 1]],
			"All": [],
			"Ordered": [["status", "in", ["Ordered", "Partially Ordered"]]],
			"Expired": [["status", "=", "Expired"]],
		},
		"search": ("name", ("Quotation Item", "item_name"), ("Quotation Item", "item_code")),
		# open and inside its last week
		"urgent": lambda: [
			["status", "=", "Open"],
			["is_active", "=", 1],
			# an answered quotation waits on us, not on the customer
			["portal_response", "is", "not set"],
			["valid_till", "between", [today(), add_days(today(), 7)]],
		],
		"deadline": "valid_till",
	},
	"orders": {
		"doctype": "Sales Order",
		"fields": ORDER_LIST_FIELDS,
		"date_field": "transaction_date",
		"filters": {},
		"tabs": {
			"Active": [["status", "in", ACTIVE_ORDER_STATUSES]],
			"All": [],
			"Completed": [["status", "=", "Completed"]],
			"Closed": [["status", "=", "Closed"]],
		},
		"search": ("name", ("Sales Order Item", "item_name"), ("Sales Order Item", "item_code")),
		# still running, not fully delivered, and past its delivery date
		"urgent": lambda: [
			["status", "in", ACTIVE_ORDER_STATUSES],
			["per_delivered", "<", 100],
			["delivery_date", "<", today()],
		],
		"deadline": "delivery_date",
	},
	"invoices": {
		"doctype": "Sales Invoice",
		"fields": INVOICE_LIST_FIELDS,
		"date_field": "posting_date",
		"filters": {},
		"tabs": {
			"Outstanding": [["outstanding_amount", ">", 0]],
			"All": [],
			"Overdue": [["status", "in", OVERDUE_INVOICE_STATUSES]],
			"Paid": [["status", "=", "Paid"]],
		},
		"search": ("name", ("Sales Invoice Item", "item_name"), ("Sales Invoice Item", "item_code")),
		# unpaid, and overdue (an earlier instalment can be) or due within three days
		"urgent": lambda: [
			["outstanding_amount", ">", 0],
			Criterion.any(
				[
					frappe.qb.DocType("Sales Invoice").status.isin(OVERDUE_INVOICE_STATUSES),
					frappe.qb.DocType("Sales Invoice").due_date <= add_days(today(), 3),
				]
			),
		],
		"deadline": "due_date",
	},
	"shipments": {
		"doctype": "Delivery Note",
		"fields": SHIPMENT_LIST_FIELDS,
		"date_field": "posting_date",
		"filters": {},
		"tabs": {
			"All": [],
			"Dispatched": [["is_return", "=", 0]],
			"Returned": [["is_return", "=", 1]],
		},
		"search": ("name", "lr_no", ("Delivery Note Item", "item_name"), ("Delivery Note Item", "item_code")),
		# nothing on a shipment falls due
		"urgent": None,
		"deadline": None,
	},
}


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
def get_home() -> dict:
	"""Everything the home page summarises, in one call."""
	return {
		# a user no customer lists under Portal Users sees nothing, and the page says why
		"linked": bool(_portal_customers()),
		"quotations": _documents("quotations"),
		"orders": _documents("orders"),
		"invoices": _documents("invoices"),
		# counted over every document: the lists above stop at LIST_LIMIT
		"summary": _home_summary(),
	}


@frappe.whitelist()
def get_quotation(name: str) -> dict:
	"""One of the customer's quotations, with only what its page shows."""
	doc = _customer_doc("Quotation", name)
	reply = {
		**_reply(doc, QUOTATION_FIELDS, ITEM_FIELDS),
		"signed": bool(doc.customer_signature),
		"signed_on": _signed_on(doc.name) if doc.customer_signature else None,
	}
	_add_revised_to([reply])
	reply["orders"] = [order.name for order in _made_against(name, "Sales Order", "prevdoc_docname", [])]
	return reply


def _signed_on(quotation: str):
	"""When the customer signed: the signed copy is rendered as they sign. Not `modified`, which
	moves whenever Desk saves the quotation, making an order from it included."""
	return frappe.db.get_value(
		"File",
		{
			"attached_to_doctype": "Quotation",
			"attached_to_name": quotation,
			"file_name": f"{quotation}-signed.pdf",
		},
		"creation",
		order_by="creation asc",
	)


@frappe.whitelist()
def get_order(name: str) -> dict:
	"""One of the customer's sales orders, with only what its page shows, and the shipments and
	invoices made against it."""
	return {
		**_reply(_customer_doc("Sales Order", name), ORDER_FIELDS, ORDER_ITEM_FIELDS),
		"shipments": _made_against(name, "Delivery Note", "against_sales_order", ["is_return"]),
		"invoices": _made_against(name, "Sales Invoice", "sales_order", ["is_return"]),
	}


def _made_against(source: str, doctype: str, link_field: str, fields: list[str]) -> list[dict]:
	"""The customer's submitted documents of `doctype` with a line made from `source`, oldest first."""
	names = frappe.get_all(f"{doctype} Item", filters={link_field: source}, pluck="parent", distinct=True)
	scoped = _portal_filters(doctype, {"name": ["in", names]}) if names else None
	if not scoped:
		return []
	return frappe.get_all(
		doctype, filters=scoped, fields=["name", *fields], order_by="creation asc, name asc"
	)


@frappe.whitelist()
def get_invoice(name: str) -> dict:
	"""One of the customer's sales invoices, with only what its page shows, and its payments."""
	doc = _customer_doc("Sales Invoice", name)
	return {
		**_reply(doc, INVOICE_FIELDS, INVOICE_ITEM_FIELDS),
		"payments": _payments(doc.name),
		# a credit note made against it is money back the customer may net off before paying
		"credit_notes": frappe.get_all(
			"Sales Invoice",
			filters=_portal_filters("Sales Invoice", {"is_return": 1, "return_against": doc.name})
			or {"name": ""},
			pluck="name",
			order_by="posting_date asc, name asc",
		),
		"party_total": get_total_in_party_account_currency(doc),
	}


@frappe.whitelist()
def get_shipment(name: str) -> dict:
	"""One of the customer's delivery notes, with the order lines it delivers against."""
	doc = _customer_doc("Delivery Note", name)
	return {
		**_pick(doc, SHIPMENT_FIELDS),
		"items": _item_rows(doc, SHIPMENT_ITEM_FIELDS),
		"order_lines": _order_lines(doc),
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

	doctype = config["doctype"]
	scoped = _portal_filters(doctype, config["filters"])
	if scoped is None:
		return {"rows": [], "total": 0, "counts": dict.fromkeys(config["tabs"], 0), **_sizes(page_length)}

	scope = [
		[field, *value] if isinstance(value, list) else [field, "=", value] for field, value in scoped.items()
	]
	counts = {name: _count(doctype, scope + conditions) for name, conditions in config["tabs"].items()}

	conditions = scope + config["tabs"][tab]
	term = (search or "").strip()
	matching = _search_condition(doctype, config["search"], term) if term else None
	start = max(cint(start), 0)

	urgent = conditions + config["urgent"]() if config["urgent"] else None
	urgent_total = _list_count(doctype, urgent, matching) if urgent else 0
	names = []
	if start < urgent_total:
		names = _list_query(
			doctype,
			urgent,
			matching,
			fields=["name"],
			order_by=f"{config['deadline']} asc, creation desc",
			offset=start,
			limit=page_length,
		).run(pluck=True)

	# the rest leave the urgent ones out through a subquery, not a list of their names
	table = frappe.qb.DocType(doctype)
	not_urgent = table.name.notin(_list_query(doctype, urgent, matching, fields=["name"])) if urgent else None
	wanted = page_length - len(names)
	if wanted:
		names += _list_query(
			doctype,
			conditions,
			matching,
			not_urgent,
			fields=["name"],
			order_by=f"{config['date_field']} desc, creation desc",
			offset=max(start - urgent_total, 0),
			limit=wanted,
		).run(pluck=True)

	return {
		"rows": _list_rows(kind, config, names),
		"total": urgent_total + _list_count(doctype, conditions, matching, not_urgent),
		"counts": counts,
		**_sizes(page_length),
	}


def _sizes(page_length: int) -> dict:
	"""The page size used, and the ones the list's size buttons offer: the page draws them from here."""
	return {"page_length": page_length, "page_lengths": LIST_PAGE_LENGTHS}


def _list_rows(kind: str, config: dict, names: list[str]) -> list[dict]:
	"""The list fields of these documents, in the order given, each with its item names."""
	if not names:
		return []
	found = {
		row.name: row
		for row in frappe.get_all(config["doctype"], filters={"name": ["in", names]}, fields=config["fields"])
	}
	rows = _add_item_names(config["doctype"], [found[name] for name in names if name in found])
	if kind == "quotations":
		_add_revised_to(rows)
	_add_last_dates(kind, rows)
	return rows


def _add_last_dates(kind: str, rows: list[dict]) -> None:
	"""When an order was last delivered against, and when an invoice was last paid: the dates their
	notes show. The promised delivery date and the invoice date are not those."""
	names = [row.name for row in rows]
	if not names or kind not in ("orders", "invoices"):
		return

	if kind == "orders":
		note, line = frappe.qb.DocType("Delivery Note"), frappe.qb.DocType("Delivery Note Item")
		query = (
			frappe.qb.from_(line)
			.join(note)
			.on(note.name == line.parent)
			.select(line.against_sales_order, Max(note.posting_date))
			.where(line.against_sales_order.isin(names))
			.where((note.docstatus == 1) & (note.is_return == 0))
			.groupby(line.against_sales_order)
		)
		field = "last_delivery"
	else:
		entry, reference = frappe.qb.DocType("Payment Entry"), frappe.qb.DocType("Payment Entry Reference")
		query = (
			frappe.qb.from_(reference)
			.join(entry)
			.on(entry.name == reference.parent)
			.select(reference.reference_name, Max(entry.posting_date))
			.where(reference.reference_doctype == "Sales Invoice")
			.where(reference.reference_name.isin(names))
			.where(entry.docstatus == 1)
			.groupby(reference.reference_name)
		)
		field = "last_payment"

	dates = dict(query.run())
	for row in rows:
		row[field] = dates.get(row.name)


def _add_revised_to(quotations: list[dict]) -> None:
	"""Each quotation's latest revision, when that is a newer one the customer can see.

	Every revision points at the first version through `revision_of`, and ERPNext flags the
	latest version of the group with `is_latest_revision`."""
	first = {q["name"]: q.get("revision_of") or q["name"] for q in quotations}
	# as on the list itself, a Replied quotation is not shown
	scoped = _portal_filters("Quotation", {"is_latest_revision": 1, "status": ["!=", "Replied"]})
	latest = {}
	if first and scoped:
		groups = list(set(first.values()))
		for row in frappe.get_all(
			"Quotation",
			filters=scoped,
			or_filters={"name": ["in", groups], "revision_of": ["in", groups]},
			fields=["name", "revision_of"],
		):
			latest[row.revision_of or row.name] = row.name
	for quotation in quotations:
		newest = latest.get(first[quotation["name"]])
		quotation["revised_to"] = newest if newest != quotation["name"] else None


def _search_condition(doctype: str, fields: tuple, term: str):
	"""Either-or condition for a list search. A field of the items table is (its doctype, the field):
	it is matched in a subquery, so the list never joins the items table and so never returns or
	counts a document once per matching line."""
	# the customer's text is matched as typed: % and _ are not wildcards here
	escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
	like = f"%{escaped}%"
	table = frappe.qb.DocType(doctype)
	either = [table[field].like(like) for field in fields if isinstance(field, str)]
	by_child: dict[str, list[str]] = {}
	for child_doctype, field in (field for field in fields if isinstance(field, tuple)):
		by_child.setdefault(child_doctype, []).append(field)
	for child_doctype, child_fields in by_child.items():
		child = frappe.qb.DocType(child_doctype)
		lines = (
			frappe.qb.from_(child)
			.select(child.parent)
			.where(child.parenttype == doctype)
			.where(Criterion.any([child[field].like(like) for field in child_fields]))
		)
		either.append(table.name.isin(lines))
	return Criterion.any(either)


def _list_query(doctype: str, filters: list, *conditions, **kwargs):
	"""A query over `filters`, narrowed by any extra conditions (a search, the urgent exclusion). A
	filter that is a query condition rather than a [field, operator, value] list is one of those too."""
	plain = [condition for condition in filters if isinstance(condition, list)]
	conditions = (*(condition for condition in filters if not isinstance(condition, list)), *conditions)
	query = frappe.qb.get_query(doctype, filters=plain, **kwargs)
	for condition in conditions:
		if condition is not None:
			query = query.where(condition)
	return query


def _list_count(doctype: str, filters: list, *conditions) -> int:
	return _list_query(doctype, filters, *conditions, fields=[{"COUNT": "*", "as": "n"}]).run(pluck=True)[0]


def _count(doctype: str, filters: list) -> int:
	rows = frappe.get_all(doctype, filters=filters, fields=[{"COUNT": "*", "as": "n"}])
	return rows[0].n if rows else 0


def _documents(kind: str) -> list[dict]:
	"""The customer's latest documents of one list, newest first, each with its item names."""
	config = LIST_PAGES[kind]
	scoped = _portal_filters(config["doctype"], config["filters"])
	if scoped is None:
		return []

	documents = frappe.get_all(
		config["doctype"],
		filters=scoped,
		fields=config["fields"],
		# documents dated the same day come newest-created first, not in whatever order the database likes
		order_by=f"{config['date_field']} desc, creation desc",
		limit=LIST_LIMIT,
	)
	documents = _add_item_names(config["doctype"], documents)
	if kind == "quotations":
		_add_revised_to(documents)
	_add_last_dates(kind, documents)
	return documents


def _customer_doc(doctype: str, name: str):
	"""The document, if it is one of the customer's submitted ones. Anything else is not found."""
	scoped = _portal_filters(doctype, {"name": name})
	if scoped is None or not frappe.db.exists(doctype, scoped):
		raise frappe.DoesNotExistError
	return frappe.get_doc(doctype, name)


def _reply(doc, fields: tuple[str, ...], item_fields: tuple[str, ...]) -> dict:
	return {
		**_pick(doc, fields),
		"items": _item_rows(doc, item_fields),
		"taxes": [_pick(row, TAX_FIELDS) for row in doc.taxes],
	}


def _item_rows(doc, fields: tuple[str, ...]) -> list[dict]:
	"""The document's lines, each with its photo when the default print format shows photos.
	A private photo stays private: its line goes without, as on a line with no photo."""
	show = _print_shows_item_images(doc.doctype)
	return [{**_pick(row, fields), "image": _public_file(row.image) if show else ""} for row in doc.items]


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


def _home_summary() -> dict:
	"""Home's figures and each list's size, counted in the database rather than from a capped list."""
	return {
		"totals": {kind: _total(kind) for kind in ("quotations", "orders", "invoices")},
		"quotations": _aggregate(
			"Quotation",
			# only the ones that need the customer: an answered quotation waits on us, and a lapsed one
			# can no longer be answered, though the daily job may not have marked it Expired yet
			{"status": "Open", "is_active": 1, "portal_response": ["is", "not set"]},
			{"count": ("COUNT", "*"), "next_expiry": ("MIN", "valid_till")},
			or_filters=[["valid_till", "is", "not set"], ["valid_till", ">=", today()]],
		),
		"orders": {
			**_aggregate(
				"Sales Order",
				{"status": ["in", ACTIVE_ORDER_STATUSES], "per_delivered": ["<", 100]},
				{"count": ("COUNT", "*"), "next_delivery": ("MIN", "delivery_date")},
			),
			"late": _aggregate(
				"Sales Order",
				{
					"status": ["in", ACTIVE_ORDER_STATUSES],
					"per_delivered": ["<", 100],
					"delivery_date": ["<", today()],
				},
				{"count": ("COUNT", "*")},
			)["count"],
		},
		"shipments": _active_order_shipments(),
		"invoices": {
			**_aggregate("Sales Invoice", {"outstanding_amount": [">", 0]}, {"count": ("COUNT", "*")}),
			"owed": _owed_by_currency(),
			# by status, as the Overdue tab counts them
			"overdue": _aggregate(
				"Sales Invoice",
				{"outstanding_amount": [">", 0], "status": ["in", OVERDUE_INVOICE_STATUSES]},
				{"count": ("COUNT", "*")},
			)["count"],
		},
	}


def _owed_by_currency() -> list[dict]:
	"""What is left to pay, per currency: an invoice keeps it in its party account's currency, and two
	currencies cannot be added up."""
	scoped = _portal_filters("Sales Invoice", {"outstanding_amount": [">", 0]})
	if not scoped:
		return []
	return frappe.get_all(
		"Sales Invoice",
		filters=scoped,
		fields=["party_account_currency as currency", {"SUM": "outstanding_amount", "as": "amount"}],
		group_by="party_account_currency",
		order_by="amount desc",
	)


def _total(kind: str) -> int:
	config = LIST_PAGES[kind]
	scoped = _portal_filters(config["doctype"], config["filters"])
	return _count(config["doctype"], scoped) if scoped else 0


def _aggregate(
	doctype: str, filters: dict, columns: dict[str, tuple[str, str]], or_filters: list | None = None
) -> dict:
	"""One row of aggregates over the customer's documents, as {name: value}."""
	scoped = _portal_filters(doctype, filters)
	row = None
	if scoped:
		fields = [{function: column, "as": name} for name, (function, column) in columns.items()]
		row = frappe.get_all(doctype, filters=scoped, or_filters=or_filters, fields=fields)[0]
	# a count or a sum of nothing is 0; the earliest or latest date of nothing is None
	return {
		name: (row or {}).get(name) or (0 if function in ("COUNT", "SUM") else None)
		for name, (function, _column) in columns.items()
	}


def _active_order_shipments() -> dict:
	"""Dispatches (not returns) against orders that are still running: how many, and the latest."""
	scoped = _portal_filters("Sales Order", {"status": ["in", ACTIVE_ORDER_STATUSES]})
	orders = frappe.get_all("Sales Order", filters=scoped, pluck="name") if scoped else []
	shipments = (
		frappe.get_all(
			"Delivery Note Item",
			filters={"parenttype": "Delivery Note", "against_sales_order": ["in", orders]},
			pluck="parent",
			distinct=True,
		)
		if orders
		else []
	)
	if not shipments:
		return {"count": 0, "last": None}
	return _aggregate(
		"Delivery Note",
		{"name": ["in", shipments], "is_return": 0},
		{"count": ("COUNT", "*"), "last": ("MAX", "posting_date")},
	)


def _payments(invoice: str) -> list[dict]:
	"""What the customer has paid against one invoice, oldest first."""
	allocations = frappe.get_all(
		"Payment Entry Reference",
		filters={
			"parenttype": "Payment Entry",
			"reference_doctype": "Sales Invoice",
			"reference_name": invoice,
		},
		fields=["parent", "allocated_amount"],
	)
	if not allocations:
		return []

	scoped = _portal_filters("Payment Entry", {"name": ["in", [row.parent for row in allocations]]})
	if scoped is None:
		return []

	entries = {
		entry.name: entry
		for entry in frappe.get_all(
			"Payment Entry",
			filters=scoped,
			fields=["name", "posting_date", "mode_of_payment", "reference_no"],
		)
	}
	payments = [
		{**entries[row.parent], "allocated_amount": row.allocated_amount}
		for row in allocations
		if row.parent in entries
	]
	return sorted(payments, key=lambda payment: (payment["posting_date"], payment["name"]))


def _order_lines(shipment) -> list[dict]:
	"""Every line of the orders a shipment delivers against, for its "Yet to ship" column."""
	orders = sorted({row.against_sales_order for row in shipment.items if row.against_sales_order})
	if not orders:
		return []

	scoped = _portal_filters("Sales Order", {"name": ["in", orders]})
	visible = frappe.get_all("Sales Order", filters=scoped, pluck="name") if scoped else []
	if not visible:
		return []

	return frappe.get_all(
		"Sales Order Item",
		filters={"parenttype": "Sales Order", "parent": ["in", visible]},
		fields=["parent as sales_order", "item_code", "qty", "delivered_qty"],
	)


def _pick(doc, fields: tuple[str, ...]) -> dict:
	return {field: doc.get(field) for field in fields}


def _add_item_names(doctype: str, documents: list[dict]) -> list[dict]:
	"""Gives each document its item names, for the list preview."""
	item_names = _item_names(doctype, [document.name for document in documents])
	for document in documents:
		document["items"] = item_names.get(document.name, [])
	return documents


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


# What a customer can say about a quotation, and how the quotation records it. `portal_response`
# is the customer's answer, not a pipeline status: only the portal writes it, and Desk shows it
# read-only.
PORTAL_QUOTATION_ACTIONS = {
	"accept": "Accepted",
	"changes": "Changes Requested",
	"reject": "Rejected",
}


def _answer_headline(action: str, who: str, name: str) -> str:
	"""How an answer reads in the thread and the notification. Whole sentences, so a translation
	can put the words in its own order."""
	if action == "accept":
		return _("{0} accepted quotation {1}").format(who, name)
	if action == "changes":
		return _("{0} requested changes to quotation {1}").format(who, name)
	return _("{0} rejected quotation {1}").format(who, name)


PORTAL_SIGNATURE_FIELD = "customer_signature"


def protect_quotation_signature(doc, method: str | None = None) -> None:
	"""The customer's answer is theirs: only the portal writes it, and the signature only once.

	Both fields are read-only in Desk, but the REST API does not stop a Sales User from setting
	them, which would skip the portal's checks (a PNG signature, a quotation still open)."""
	before = doc.get_doc_before_save()
	previous = before.get(PORTAL_SIGNATURE_FIELD) if before else None
	if previous and previous != doc.get(PORTAL_SIGNATURE_FIELD):
		frappe.throw(
			_("The customer's signature cannot be changed or removed once it is given."),
			frappe.PermissionError,
		)

	if frappe.flags.portal_answer == doc.name:
		return
	for field in (PORTAL_SIGNATURE_FIELD, "portal_response"):
		if ((before.get(field) if before else None) or None) != (doc.get(field) or None):
			frappe.throw(
				_("Only the customer can answer a quotation, on the portal."), frappe.PermissionError
			)


SIGNATURE_PREFIX = "data:image/png;base64,"
# a drawing of a signature is a few KB; the cap is only there to stop abuse
SIGNATURE_MAX_BYTES = 512 * 1024


def _store_signature(name: str, signature: str) -> None:
	"""Record the drawing on the quotation so its print format can show it.

	Only a PNG payload is accepted. Anything else is a URL the print renderer
	would fetch server-side on every print, from wherever the caller points it.
	"""
	if not signature.startswith(SIGNATURE_PREFIX) or len(signature) > SIGNATURE_MAX_BYTES:
		frappe.throw(_("That is not a valid signature."))

	doc = frappe.get_doc("Quotation", name)
	doc.set(PORTAL_SIGNATURE_FIELD, signature)
	# save, not db_set: the hook that keeps the signature write-once must run. The flag is how that
	# hook knows the portal is writing, which a REST call cannot set.
	frappe.flags.portal_answer = name
	try:
		doc.save(ignore_permissions=True)
	finally:
		frappe.flags.portal_answer = None


def attach_signed_copy(name: str, comment: str) -> None:
	"""Render the signed quotation, attach it, and link it from the comment.

	The file goes on the document, not the comment: Desk's timeline logs attachments
	on a document and renders nothing inside a comment bubble.
	"""
	url = (
		frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"{name}-signed.pdf",
				"is_private": 1,
				"content": frappe.get_print("Quotation", name, as_pdf=True),
				"attached_to_doctype": "Quotation",
				"attached_to_name": name,
			}
		)
		.insert(ignore_permissions=True)
		.file_url
	)

	content = frappe.db.get_value("Comment", comment, "content") or ""
	frappe.db.set_value(
		"Comment",
		comment,
		"content",
		f'{content}<br><a href="{url}" target="_blank">{name}-signed.pdf</a>',
		update_modified=False,
	)


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=10, seconds=60 * 60, user_based=True, ip_based=False)
def submit_quotation_response(
	name: str, action: str, message: str | None = None, signature: str | None = None
) -> dict:
	"""Record a customer's answer to a quotation and tell whoever sent it."""
	if action not in PORTAL_QUOTATION_ACTIONS:
		frappe.throw(_("Unknown action {0}").format(action))
	# the signature is what makes an acceptance final; without one it could be answered again
	if action == "accept" and not signature:
		frappe.throw(_("Please sign the quotation to accept it."))
	if action == "changes" and not (message or "").strip():
		frappe.throw(_("Please say what should change."))

	scoped = _portal_filters("Quotation", {"name": name})
	if scoped is None or not frappe.db.exists("Quotation", scoped):
		raise frappe.DoesNotExistError

	# Asking for changes leaves the conversation open; signing or rejecting ends it. The row
	# is locked for the rest of the transaction, so two answers sent at once are serialised
	# and the second one sees the first.
	answered = frappe.db.get_value(
		"Quotation",
		name,
		[PORTAL_SIGNATURE_FIELD, "portal_response", "status", "is_active", "valid_till"],
		as_dict=True,
		for_update=True,
	)
	if answered.get(PORTAL_SIGNATURE_FIELD) or answered.get("portal_response") == "Rejected":
		frappe.throw(_("You have already answered this quotation."))
	# ordered, lost, expired or replaced by a revision: ERPNext can no longer make an order from it.
	# A lapsed one counts as expired before the daily job gets round to marking it.
	lapsed = answered.valid_till and getdate(answered.valid_till) < getdate(today())
	if answered.status != "Open" or not answered.is_active or lapsed:
		frappe.throw(_("This quotation can no longer be answered."))

	response = PORTAL_QUOTATION_ACTIONS[action]
	who = frappe.utils.get_fullname(frappe.session.user)
	headline = _answer_headline(action, who, name)
	body = (message or "").strip()

	if action == "accept":
		_store_signature(name, signature)
	frappe.db.set_value("Quotation", name, "portal_response", response)

	# the comment is HTML, where a typed line break would otherwise collapse into a space
	note = frappe.utils.escape_html(body).replace("\n", "<br>")
	comment = frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Comment",
			"reference_doctype": "Quotation",
			"reference_name": name,
			"comment_email": frappe.session.user,
			"comment_by": who,
			"published": 1,
			"content": f"{headline}<br>{note}" if body else headline,
		}
	).insert(ignore_permissions=True)

	pending = False
	if action == "accept":
		try:
			attach_signed_copy(name, comment.name)
		except Exception:
			# a failed render must not cost the customer their acceptance; a background job
			# tries once more and the portal holds the comment back until it lands
			frappe.log_error("Failed to render the signed quotation copy")
			frappe.enqueue(
				"erpnext.portal.customer_portal.attach_signed_copy",
				queue="short",
				# after commit, so the job cannot start before the signature it renders is saved
				enqueue_after_commit=True,
				name=name,
				comment=comment.name,
			)
			pending = True

	notify_portal_response("Quotation", name, headline, body)
	# `pending` tells the portal to hold the comment back until its copy lands
	return {"ok": True, "comment": comment.name, "pending": pending}


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


SIGNED_COPY_LINK = re.compile(r'<br><a href="([^"]+)"[^>]*>([^<]+-signed\.pdf)</a>$')


def get_portal_users_for_document(doctype: str, name: str) -> list[str]:
	"""Portal users of the customer a document belongs to. A User's name is its email."""
	party_field = PORTAL_DOCTYPES.get(doctype)
	if not party_field:
		return []

	# the party guards the list queries use, so a Quotation to a Lead resolves to nobody. Whether the
	# customer may see the document (docstatus) is for the caller to check.
	for field, expected in PORTAL_EXTRA_FILTERS.get(doctype, {}).items():
		if frappe.db.get_value(doctype, name, field) != expected:
			return []

	customer = frappe.db.get_value(doctype, name, party_field)
	if not customer:
		return []

	portal_user = frappe.qb.DocType("Portal User")
	return (
		frappe.qb.from_(portal_user)
		.select(portal_user.user)
		.where(portal_user.parent == customer)
		.where(portal_user.parenttype == "Customer")
	).run(pluck="user")


def protect_portal_comment(doc, method: str | None = None) -> None:
	"""A customer's own words are not the team's to rewrite.

	Desk lets a System Manager edit any comment (desk/form/utils.py allows the owner
	or Administrator). That is fine between colleagues, but a comment written from the
	portal is a customer's statement on their own document, so only its author may
	change what it says.
	"""
	if doc.comment_type != "Comment":
		return

	before = doc.get_doc_before_save()
	if not before or before.content == doc.content:
		return
	if doc.owner == frappe.session.user:
		return
	# Portal User is the source of truth for "this person is a contact of that customer".
	# User.user_type is not: a portal login may be provisioned either way.
	if doc.owner not in get_portal_users_for_document(doc.reference_doctype, doc.reference_name):
		return

	frappe.throw(
		_("This comment was written by the customer and can only be edited by them."),
		frappe.PermissionError,
	)


def notify_customer_of_comment(doc, method: str | None = None) -> None:
	"""Tell the customer when a comment on one of their documents becomes visible to them."""
	if doc.comment_type != "Comment" or not doc.published:
		return
	# only a document the customer can open: a draft or cancelled one, or a doctype the portal has
	# no page for, would land them on "not found"
	if doc.reference_doctype not in COMMENT_DOCTYPES or not doc.reference_name:
		return
	if frappe.db.get_value(doc.reference_doctype, doc.reference_name, "docstatus") != 1:
		return
	# on_update fires on every save, including the one right after insert; only a
	# genuine 0 -> 1 publish on an existing comment is news
	if method == "on_update":
		before = doc.get_doc_before_save()
		if not before or before.published == doc.published:
			return

	recipients = get_portal_users_for_document(doc.reference_doctype, doc.reference_name)
	if not recipients:
		return
	# only the team's side of the conversation is news to the customer; their own
	# comments and their own acceptance already happened in front of them
	if doc.owner in recipients:
		return

	notify_portal_response(
		doc.reference_doctype,
		doc.reference_name,
		_("New comment on {0}").format(doc.reference_name),
		doc.content or "",
		recipients=recipients,
	)


# The address book a customer may keep for themselves. Anything outside this list --
# the links that decide whose address it is, above all -- is the server's to set.
PORTAL_ADDRESS_FIELDS = (
	"address_title",
	"address_type",
	"address_line1",
	"address_line2",
	"city",
	"state",
	"country",
	"pincode",
	"email_id",
	"phone",
	"is_primary_address",
	"is_shipping_address",
)


def _customer_address_filters(customers: list[str]) -> list:
	return [
		["Dynamic Link", "link_doctype", "=", "Customer"],
		["Dynamic Link", "link_name", "in", customers],
		["disabled", "=", 0],
	]


@frappe.whitelist()
def get_portal_addresses() -> list[dict]:
	"""The signed-in customer's address book, whoever in the company wrote it.

	Deliberately not scoped to the rows this user created: an address a salesperson
	entered is still the customer's own, and hiding it is what makes the old portal's
	list look empty.
	"""
	customers = _portal_customers()
	if not customers:
		return []

	addresses = frappe.get_all(
		"Address",
		filters=_customer_address_filters(customers),
		fields=["name", *PORTAL_ADDRESS_FIELDS],
		distinct=True,
		ignore_permissions=True,
	)
	# sorted here because frappe drops ORDER BY from a distinct query on Postgres
	return sorted(
		addresses,
		key=lambda a: (
			not a.is_primary_address,
			not a.is_shipping_address,
			(a.address_title or "").casefold(),
		),
	)


@frappe.whitelist()
def get_portal_address_options() -> dict:
	"""What the address dialog's two pickers offer.

	Read from the site rather than written into the page, so a country added here or
	an address type added upstream shows up without anyone editing the portal.
	"""
	if not _portal_customers():
		raise frappe.PermissionError

	address_type = frappe.get_meta("Address").get_field("address_type")
	options = (address_type.options or "").split("\n") if address_type else []
	return {
		"address_types": [option for option in options if option],
		"countries": frappe.get_all("Country", pluck="name", order_by="name", ignore_permissions=True),
		"default_country": frappe.db.get_single_value("Global Defaults", "country") or "",
	}


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=30, seconds=60 * 60, user_based=True, ip_based=False)
def save_portal_address(values: dict | str, name: str | None = None) -> str:
	"""Add an address to the customer's book, or change one already in it."""
	customers = _portal_customers()
	if not customers:
		raise frappe.PermissionError

	values = frappe.parse_json(values) if isinstance(values, str) else dict(values or {})

	if name:
		if not frappe.db.exists(
			"Address", [["Address", "name", "=", name], *_customer_address_filters(customers)]
		):
			raise frappe.DoesNotExistError
		doc = frappe.get_doc("Address", name)
	else:
		doc = frappe.new_doc("Address")
		customer = values.get("customer")
		# whose address this is, is not the caller's to say
		doc.append(
			"links",
			{
				"link_doctype": "Customer",
				"link_name": customer if customer in customers else customers[0],
			},
		)

	for field in PORTAL_ADDRESS_FIELDS:
		if field in values:
			doc.set(field, values[field])

	doc.save(ignore_permissions=True)
	return doc.name


# the documents that have a page; Payment Entry is in PORTAL_DOCTYPES only to scope payments
COMMENT_DOCTYPES = ("Quotation", "Sales Order", "Sales Invoice", "Delivery Note")


@frappe.whitelist()
def get_portal_comments(doctype: str, name: str) -> list[dict]:
	"""The customer-visible conversation on one of their documents."""
	if doctype not in COMMENT_DOCTYPES:
		raise frappe.DoesNotExistError
	scoped = _portal_filters(doctype, {"name": name})
	if scoped is None or not frappe.db.exists(doctype, scoped):
		raise frappe.DoesNotExistError

	comments = frappe.get_all(
		"Comment",
		filters={
			"reference_doctype": doctype,
			"reference_name": name,
			"comment_type": "Comment",
			"published": 1,
		},
		# reference_name lets a page tell this thread from the one it showed before
		fields=["name", "reference_name", "comment_by", "comment_email", "content", "creation"],
		# newest first, like Desk's timeline: the portal's timeline renders rows in the
		# order it is handed them rather than sorting them itself
		order_by="creation desc",
		ignore_permissions=True,
	)
	if not comments:
		return []

	# one query for the whole thread rather than one per comment
	attachments = frappe.get_all(
		"File",
		filters={"attached_to_doctype": "Comment", "attached_to_name": ("in", [c.name for c in comments])},
		fields=["attached_to_name", "file_name", "file_url", "is_private"],
		ignore_permissions=True,
	)
	by_comment: dict[str, list] = {}
	for row in attachments:
		by_comment.setdefault(row.attached_to_name, []).append(
			{"file_name": row.file_name, "file_url": row.file_url, "is_private": row.is_private}
		)
	for comment in comments:
		# a staff member's login email is theirs to give out; the name is enough to show
		if comment.comment_email != frappe.session.user:
			comment.comment_email = ""
		comment["attachments"] = by_comment.get(comment.name, [])

		# Desk shows the signed copy as a link in the comment text, because its
		# timeline renders nothing else inside a bubble. The portal has its own
		# timeline, which draws attachments as chips — so move the link across
		# rather than showing the same file twice.
		found = SIGNED_COPY_LINK.search(comment.get("content") or "")
		if found:
			comment["content"] = SIGNED_COPY_LINK.sub("", comment["content"], count=1)
			comment["attachments"].append(
				{"file_url": found.group(1), "file_name": found.group(2), "is_private": 1}
			)

	return comments


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=20, seconds=60 * 60, user_based=True, ip_based=False)
def add_portal_comment(doctype: str, name: str, content: str) -> dict:
	"""Post a comment as the signed-in portal user, and tell whoever owns the document."""
	if doctype not in COMMENT_DOCTYPES:
		raise frappe.DoesNotExistError
	# Comment.validate cleans the HTML too; this copy only tells an empty message apart
	content = sanitize_html((content or "").strip())
	if not content:
		frappe.throw(_("Write something first"))

	scoped = _portal_filters(doctype, {"name": name})
	if scoped is None or not frappe.db.exists(doctype, scoped):
		raise frappe.DoesNotExistError

	who = frappe.utils.get_fullname(frappe.session.user)
	comment = frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Comment",
			"reference_doctype": doctype,
			"reference_name": name,
			"comment_email": frappe.session.user,
			"comment_by": who,
			"published": 1,
			"content": content,
		}
	).insert(ignore_permissions=True)

	notify_portal_response(doctype, name, _("{0} commented on {1}").format(who, name), content)
	return {"name": comment.name}


@frappe.whitelist()
def get_portal_context() -> dict:
	"""Who the signed-in portal user is, and the company the portal is branded as."""
	user = frappe.session.user
	full_name, email = frappe.db.get_value("User", user, ["full_name", "email"]) or (None, None)

	return {
		"user": user,
		"full_name": full_name,
		"email": email,
		"company": _portal_company(),
	}


def _portal_company() -> dict:
	"""The company the portal is branded as: the one on the customer's latest invoice, else their latest
	order, else their latest quotation, else the site default."""
	company = None
	for doctype in ("Sales Invoice", "Sales Order", "Quotation"):
		scoped = _portal_filters(doctype)
		if scoped is None:
			break
		company = frappe.db.get_value(doctype, scoped, "company", order_by="creation desc")
		if company:
			break

	company = company or frappe.defaults.get_global_default("company")
	if not company:
		return {"name": "", "logo": ""}

	return {"name": company, "logo": _public_file(frappe.db.get_value("Company", company, "company_logo"))}


def _public_file(url: str | None) -> str:
	"""The file's URL, or nothing when it is private: that would 403 for a website user, and
	the fallback (an initial) reads better than a broken image."""
	url = url or ""
	return "" if url.startswith("/private/") else url
