# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Billing status tracking and return invoicing for Delivery Note."""

import frappe
from frappe import _
from frappe.desk.notifications import clear_doctype_notifications
from frappe.query_builder import Case
from frappe.query_builder.functions import Abs, IfNull, Sum
from frappe.utils import flt

from erpnext.controllers.item_close import validate_parent_reopen


class BillingStatusService:
	def __init__(self, doc):
		self.doc = doc

	def update_status(self, status: str) -> None:
		doc = self.doc

		if status != "Closed" and doc.status == "Closed":
			validate_parent_reopen(doc)

		doc.set_status(update=True, status=status)
		doc.notify_update()
		clear_doctype_notifications(doc)

	def update_billing_status(self, update_modified: bool = True) -> None:
		doc = self.doc
		updated_delivery_notes = [doc.name]
		if doc.is_return and doc.return_against:
			updated_delivery_notes.append(doc.return_against)

		for d in doc.get("items"):
			if d.si_detail and not d.so_detail:
				d.db_set("billed_amt", d.amount, update_modified=update_modified)
			elif d.so_detail:
				updated_delivery_notes += update_billed_amount_based_on_so(d.so_detail, update_modified)

		for dn in set(updated_delivery_notes):
			dn_doc = doc if (dn == doc.name) else frappe.get_lazy_doc("Delivery Note", dn)
			update_dn_modified = update_modified and dn != doc.return_against
			dn_doc.update_billing_percentage(update_modified=update_dn_modified)
			# Deliveries and returns of the same Sales Order row can shift which returns are settled.
			update_billing_percentage_of_returns(dn)

		doc.load_from_db()

	def make_return_invoice(self) -> None:
		from erpnext.stock.doctype.delivery_note.mapper import make_sales_invoice

		creditable_qty = get_creditable_qty(self.doc)
		if not any(creditable_qty.values()):
			frappe.msgprint(_("No Credit Note was created because the returned items were not invoiced"))
			return

		try:
			return_invoice = make_sales_invoice(self.doc.name)
			return_invoice.is_return = True
			limit_to_creditable_qty(return_invoice, creditable_qty)
			return_invoice.save()
			return_invoice.submit()

			credit_note_link = frappe.utils.get_link_to_form("Sales Invoice", return_invoice.name)

			frappe.msgprint(_("Credit Note {0} has been created automatically").format(credit_note_link))
		except Exception:
			frappe.throw(
				_(
					"Could not create Credit Note automatically, please uncheck 'Issue Credit Note' and submit again"
				)
			)


def get_creditable_qty(return_doc) -> dict:
	original_rows = get_original_rows(return_doc)
	if not original_rows:
		return {}

	available = get_billed_stock_qty({row.name for row in original_rows})
	apply_earlier_credits(available, original_rows, return_doc)
	settled_qty = get_settled_return_qty(return_doc.return_against)

	creditable_qty = {}
	rows = [d for d in return_doc.items if d.dn_detail] + [d for d in return_doc.items if not d.dn_detail]
	for row in rows:
		sources = (
			[row.dn_detail]
			if row.dn_detail
			else [d.name for d in original_rows if d.item_code == row.item_code]
		)
		factor = flt(row.conversion_factor) or 1
		returned = abs(flt(row.stock_qty) or flt(row.qty) * factor)
		needed = max(returned - flt(settled_qty.get(row.name)) * factor, 0)
		creditable_qty[row.name] = flt(take_credit(available, sources, needed) / factor, 6)

	return creditable_qty


def get_original_rows(return_doc) -> list:
	linked = {d.dn_detail for d in return_doc.items if d.dn_detail}
	item_codes = {d.item_code for d in return_doc.items}
	rows = {}
	fields = ["name", "item_code", "idx"]
	if linked:
		for row in frappe.get_all(
			"Delivery Note Item", filters={"name": ("in", list(linked))}, fields=fields
		):
			rows[row.name] = row

	if return_doc.return_against:
		for row in frappe.get_all(
			"Delivery Note Item",
			filters={"parent": return_doc.return_against, "item_code": ("in", list(item_codes))},
			fields=fields,
		):
			rows[row.name] = row

	return sorted(rows.values(), key=lambda row: row.idx)


def take_credit(available: dict, sources: list, needed: float) -> float:
	taken = 0.0
	for source in sources:
		take = min(needed - taken, max(flt(available.get(source)), 0))
		available[source] = flt(available.get(source)) - take
		taken += take

	return taken


def apply_earlier_credits(available: dict, original_rows: list, return_doc) -> None:
	earlier_credits = get_earlier_credits(original_rows, return_doc)
	for earlier in earlier_credits:
		if earlier.dn_detail in available:
			take_credit(available, [earlier.dn_detail], earlier.stock_qty)

	for earlier in earlier_credits:
		if not earlier.dn_detail:
			sources = [d.name for d in original_rows if d.item_code == earlier.item_code]
			take_credit(available, sources, earlier.stock_qty)


def get_billed_stock_qty(original_rows: set) -> dict:
	si = frappe.qb.DocType("Sales Invoice")
	sii = frappe.qb.DocType("Sales Invoice Item")
	invoiced = {
		row.dn_detail: row
		for row in (
			frappe.qb.from_(sii)
			.join(si)
			.on(si.name == sii.parent)
			.select(sii.dn_detail, Sum(sii.stock_qty).as_("stock_qty"), Sum(sii.amount).as_("amount"))
			.where(
				sii.dn_detail.isin(list(original_rows))
				& (sii.docstatus == 1)
				& ((si.is_return == 0) | (si.update_billed_amount_in_delivery_note == 1))
			)
			.groupby(sii.dn_detail)
		).run(as_dict=True)
	}

	billed_qty = {}
	for row in frappe.get_all(
		"Delivery Note Item",
		filters={"name": ("in", list(original_rows))},
		fields=["name", "billed_amt", "rate", "qty", "conversion_factor"],
	):
		factor = flt(row.conversion_factor) or 1
		billed_qty[row.name] = get_row_billed_qty(row, invoiced.get(row.name)) * factor

	return billed_qty


def get_row_billed_qty(row, invoiced) -> float:
	direct_qty = flt(invoiced.stock_qty) / (flt(row.conversion_factor) or 1) if invoiced else 0.0
	if not flt(row.rate):
		return direct_qty if invoiced else flt(row.qty)

	direct_amount = flt(invoiced.amount) if invoiced else 0.0
	order_billed_amount = max(flt(row.billed_amt) - direct_amount, 0.0)
	return direct_qty + flt(order_billed_amount / flt(row.rate), 6)


def get_earlier_credits(original_rows: list, return_doc) -> list:
	dn = frappe.qb.DocType("Delivery Note")
	dni = frappe.qb.DocType("Delivery Note Item")
	sii = frappe.qb.DocType("Sales Invoice Item")
	condition = dni.dn_detail.isin([row.name for row in original_rows])
	if return_doc.return_against:
		condition |= dn.return_against == return_doc.return_against

	return (
		frappe.qb.from_(sii)
		.join(dni)
		.on(dni.name == sii.dn_detail)
		.join(dn)
		.on(dn.name == dni.parent)
		.select(dni.dn_detail, dni.item_code, Abs(Sum(sii.stock_qty)).as_("stock_qty"))
		.where(
			condition
			& (dn.docstatus == 1)
			& (dn.is_return == 1)
			& (dn.name != return_doc.name)
			& (sii.docstatus == 1)
			& (sii.qty < 0)
		)
		.groupby(dni.name, dni.dn_detail, dni.item_code)
	).run(as_dict=True)


def get_settled_return_qty(delivery_note: str) -> dict[str, float]:
	"""Qty of each return row against `delivery_note` that its invoices already deducted.

	An invoice made from a Delivery Note leaves out the returned qty. Once the original row is
	invoiced up to its net qty, these returns are settled and need no credit note. Earlier
	returns are settled first.
	"""
	dn = frappe.qb.DocType("Delivery Note")
	dn_item = frappe.qb.DocType("Delivery Note Item")
	return_rows = (
		frappe.qb.from_(dn_item)
		.join(dn)
		.on(dn.name == dn_item.parent)
		.select(dn_item.name, dn_item.dn_detail, dn_item.qty, dn_item.conversion_factor)
		.where(
			(dn.return_against == delivery_note)
			& (dn.is_return == 1)
			& (dn.docstatus == 1)
			& (IfNull(dn_item.dn_detail, "") != "")
		)
		.orderby(dn.posting_date, dn.posting_time, dn.name)
		.run(as_dict=True)
	)
	if not return_rows:
		return {}

	original_rows = {
		row.name: row
		for row in frappe.get_all(
			"Delivery Note Item",
			filters={"parent": delivery_note, "parenttype": "Delivery Note"},
			fields=["name", "qty", "conversion_factor", "so_detail", "si_detail"],
		)
	}
	invoiced_qty = get_invoiced_qty_against_dn(delivery_note=delivery_note)
	overbilled_qty = get_overbilled_qty_of_delivery_rows(
		{row.so_detail for row in original_rows.values() if row.so_detail}
	)
	# A return row can use another UOM than its original row: compare qty in the original's UOM.
	for row in return_rows:
		original_factor = flt(original_rows[row.dn_detail].conversion_factor) or 1
		row.to_original_uom = (flt(row.conversion_factor) or 1) / original_factor
		row.original_qty = abs(flt(row.qty)) * row.to_original_uom

	returned_qty = {}
	for row in return_rows:
		returned_qty[row.dn_detail] = flt(returned_qty.get(row.dn_detail)) + row.original_qty

	qty_precision = frappe.get_precision("Delivery Note Item", "qty")
	settleable_qty = {}
	for original, returned in returned_qty.items():
		returned = flt(returned, qty_precision)
		net_invoiced = flt(invoiced_qty.get(original))
		uninvoiced = flt(flt(original_rows[original].qty) - net_invoiced, qty_precision)
		# Until the net qty is fully invoiced, the next invoice still deducts the returns.
		# A row delivered from a Sales Invoice is billed there, so its returns need a credit note.
		delivered_from_invoice = bool(original_rows[original].si_detail)
		fully_invoiced = returned >= uninvoiced and not delivered_from_invoice
		settleable = max(min(returned, uninvoiced), 0) if fully_invoiced else 0
		# Billing of the Sales Order row above its net delivered qty covers returned qty.
		overbilled = flt(overbilled_qty.get(original))
		settleable_qty[original] = max(settleable - overbilled, 0)

	settled_qty = {}
	for row in return_rows:
		settled = min(row.original_qty, settleable_qty[row.dn_detail])
		settleable_qty[row.dn_detail] -= settled
		settled_qty[row.name] = flt(settled / row.to_original_uom, qty_precision)

	return settled_qty


def get_overbilled_qty_of_delivery_rows(so_details: set) -> dict[str, float]:
	"""Share the over-billed qty of each Sales Order row between its Delivery Note rows.

	Like billing against the Sales Order, it goes to the earliest deliveries first. Each row takes
	up to its returned qty that its own invoices did not bill.
	"""
	so_overbilled_stock_qty = get_so_overbilled_stock_qty(so_details)
	if not any(so_overbilled_stock_qty.values()):
		return {}

	dn = frappe.qb.DocType("Delivery Note")
	dn_item = frappe.qb.DocType("Delivery Note Item")
	delivery_rows = (
		frappe.qb.from_(dn_item)
		.join(dn)
		.on(dn.name == dn_item.parent)
		.select(dn_item.name, dn_item.parent, dn_item.so_detail, dn_item.qty, dn_item.conversion_factor)
		.where(dn_item.so_detail.isin(list(so_details)) & (dn.docstatus == 1) & (dn.is_return == 0))
		.orderby(dn.posting_date, dn.posting_time, dn.name, dn_item.idx)
		.run(as_dict=True)
	)
	# Return rows have a negative qty.
	returned_stock_qty = dict(
		frappe.qb.from_(dn_item)
		.select(dn_item.dn_detail, Sum(dn_item.stock_qty))
		.where(dn_item.dn_detail.isin([row.name for row in delivery_rows]) & (dn_item.docstatus == 1))
		.groupby(dn_item.dn_detail)
		.run()
	)
	invoiced_qty = {}
	for delivery_note in {row.parent for row in delivery_rows}:
		invoiced_qty.update(get_invoiced_qty_against_dn(delivery_note=delivery_note))

	# Rows, returns and invoices can use different UOMs: share in stock qty.
	qty_precision = frappe.get_precision("Delivery Note Item", "qty")
	overbilled_qty = {}
	for row in delivery_rows:
		factor = flt(row.conversion_factor) or 1
		returned = abs(flt(returned_stock_qty.get(row.name)))
		uninvoiced = (flt(row.qty) - flt(invoiced_qty.get(row.name))) * factor
		uninvoiced_returned = max(min(returned, uninvoiced), 0)
		share = min(uninvoiced_returned, so_overbilled_stock_qty[row.so_detail])
		so_overbilled_stock_qty[row.so_detail] -= share
		overbilled_qty[row.name] = flt(share / factor, qty_precision)

	return overbilled_qty


def get_so_overbilled_stock_qty(so_details: set) -> dict[str, float]:
	"""Stock qty of each Sales Order row invoiced above its net delivered stock qty (deliveries
	less returns), limited to the stock qty invoiced directly against the Sales Order."""
	if not so_details:
		return {}

	si = frappe.qb.DocType("Sales Invoice")
	si_item = frappe.qb.DocType("Sales Invoice Item")
	billed = (
		frappe.qb.from_(si_item)
		.join(si)
		.on(si.name == si_item.parent)
		.select(
			si_item.so_detail,
			Sum(si_item.stock_qty),
			Sum(Case().when(IfNull(si_item.dn_detail, "") == "", si_item.stock_qty).else_(0)),
		)
		.where(
			si_item.so_detail.isin(list(so_details))
			& (si_item.docstatus == 1)
			& (si.is_return == 0)
			& (si.update_stock == 0)
		)
		.groupby(si_item.so_detail)
		.run()
	)
	billed_qty = {so_detail: qty for so_detail, qty, _so_qty in billed}
	# Invoices made from a Delivery Note leave out its returns, so they do not cover them.
	billed_against_so_qty = {so_detail: so_qty for so_detail, _qty, so_qty in billed}

	# Return rows have a negative qty, so the sum is the net delivered qty.
	dn_item = frappe.qb.DocType("Delivery Note Item")
	delivered_qty = dict(
		frappe.qb.from_(dn_item)
		.select(dn_item.so_detail, Sum(dn_item.stock_qty))
		.where(dn_item.so_detail.isin(list(so_details)) & (dn_item.docstatus == 1))
		.groupby(dn_item.so_detail)
		.run()
	)

	qty_precision = frappe.get_precision("Delivery Note Item", "stock_qty")
	overbilled_qty = {}
	for so_detail in so_details:
		overbilled = flt(flt(billed_qty.get(so_detail)) - flt(delivered_qty.get(so_detail)), qty_precision)
		overbilled_qty[so_detail] = max(min(overbilled, flt(billed_against_so_qty.get(so_detail))), 0)

	return overbilled_qty


def update_billing_percentage_of_returns(delivery_note: str) -> None:
	# Side effect on other documents, like for `return_against`: keep their modified timestamp.
	for name in frappe.get_all(
		"Delivery Note",
		filters={"return_against": delivery_note, "is_return": 1, "docstatus": 1},
		pluck="name",
	):
		frappe.get_lazy_doc("Delivery Note", name).update_billing_percentage(update_modified=False)


def limit_to_creditable_qty(return_invoice, creditable_qty: dict) -> None:
	rows = []
	for row in return_invoice.items:
		qty = flt(creditable_qty.get(row.dn_detail))
		if qty:
			row.qty = -min(abs(flt(row.qty)), qty)
			rows.append(row)

	return_invoice.set("items", rows)


def update_billed_amount_based_on_so(so_detail: str, update_modified: bool = True) -> list[str]:
	# Billed against Sales Order directly
	si = frappe.qb.DocType("Sales Invoice").as_("si")
	si_item = frappe.qb.DocType("Sales Invoice Item").as_("si_item")
	sum_amount = Sum(si_item.amount).as_("amount")

	billed_against_so = (
		frappe.qb.from_(si_item)
		.join(si)
		.on(si.name == si_item.parent)
		.select(sum_amount)
		.where(
			(si_item.so_detail == so_detail)
			& ((si_item.dn_detail.isnull()) | (si_item.dn_detail == ""))
			& (si_item.docstatus == 1)
			& (si.update_stock == 0)
		)
		.run()
	)
	billed_against_so = billed_against_so and billed_against_so[0][0] or 0

	# Get all Delivery Note Item rows against the Sales Order Item row
	dn = frappe.qb.DocType("Delivery Note").as_("dn")
	dn_item = frappe.qb.DocType("Delivery Note Item").as_("dn_item")

	dn_details = (
		frappe.qb.from_(dn)
		.from_(dn_item)
		.select(dn_item.name, dn_item.amount, dn_item.si_detail, dn_item.parent)
		.where(
			(dn.name == dn_item.parent)
			& (dn_item.so_detail == so_detail)
			& (dn.docstatus == 1)
			& (dn.is_return == 0)
		)
		.orderby(dn.posting_date, dn.posting_time, dn.name)
		.run(as_dict=True)
	)

	updated_dn = []
	for dnd in dn_details:
		billed_amt_against_dn = 0

		# If delivered against Sales Invoice
		if dnd.si_detail:
			billed_amt_against_dn = flt(dnd.amount)
			billed_against_so -= billed_amt_against_dn
		else:
			# Get billed amount directly against Delivery Note
			billed_amt_against_dn = frappe.get_all(
				"Sales Invoice Item",
				filters={"dn_detail": dnd.name, "docstatus": 1},
				fields=[{"SUM": "amount", "as": "amount"}],
			)
			billed_amt_against_dn = billed_amt_against_dn[0].amount or 0 if billed_amt_against_dn else 0

		# Distribute billed amount directly against SO between DNs based on FIFO
		if billed_against_so and billed_amt_against_dn < dnd.amount:
			pending_to_bill = flt(dnd.amount) - billed_amt_against_dn
			if pending_to_bill <= billed_against_so:
				billed_amt_against_dn += pending_to_bill
				billed_against_so -= pending_to_bill
			else:
				billed_amt_against_dn += billed_against_so
				billed_against_so = 0

		frappe.db.set_value(
			"Delivery Note Item",
			dnd.name,
			"billed_amt",
			billed_amt_against_dn,
			update_modified=update_modified,
		)

		updated_dn.append(dnd.parent)

	return updated_dn


def get_invoiced_qty_against_dn(
	*, delivery_note: str | None = None, dn_detail: str | None = None
) -> dict[str, float]:
	"""Return directly invoiced qty, excluding returns that do not update DN billing."""
	si = frappe.qb.DocType("Sales Invoice").as_("si")
	si_item = frappe.qb.DocType("Sales Invoice Item").as_("si_item")

	query = (
		frappe.qb.from_(si_item)
		.join(si)
		.on(si.name == si_item.parent)
		.select(si_item.dn_detail, Sum(si_item.qty).as_("qty"))
		.where(
			(si_item.docstatus == 1) & ((si.is_return == 0) | (si.update_billed_amount_in_delivery_note == 1))
		)
		.groupby(si_item.dn_detail)
	)

	if delivery_note:
		query = query.where(si_item.delivery_note == delivery_note)
	if dn_detail:
		query = query.where(si_item.dn_detail == dn_detail)

	return {row.dn_detail: flt(row.qty) for row in query.run(as_dict=True)}


def get_invoiced_qty_based_on_so(so_detail: str) -> dict[str, float]:
	"""Invoiced qty per Delivery Note Item, distributed FIFO like the amount side."""
	si = frappe.qb.DocType("Sales Invoice").as_("si")
	si_item = frappe.qb.DocType("Sales Invoice Item").as_("si_item")

	billed_qty_against_so = (
		frappe.qb.from_(si_item)
		.join(si)
		.on(si.name == si_item.parent)
		.select(Sum(si_item.qty))
		.where(
			(si_item.so_detail == so_detail)
			& ((si_item.dn_detail.isnull()) | (si_item.dn_detail == ""))
			& (si_item.docstatus == 1)
			& (si.update_stock == 0)
		)
		.run()
	)
	billed_qty_against_so = billed_qty_against_so and billed_qty_against_so[0][0] or 0

	dn = frappe.qb.DocType("Delivery Note").as_("dn")
	dn_item = frappe.qb.DocType("Delivery Note Item").as_("dn_item")

	dn_details = (
		frappe.qb.from_(dn)
		.from_(dn_item)
		.select(dn_item.name, dn_item.qty, dn_item.returned_qty, dn_item.si_detail)
		.where(
			(dn.name == dn_item.parent)
			& (dn_item.so_detail == so_detail)
			& (dn.docstatus == 1)
			& (dn.is_return == 0)
		)
		.orderby(dn.posting_date, dn.posting_time, dn.name)
		.run(as_dict=True)
	)

	qty_map = {}
	for dnd in dn_details:
		# Cap FIFO capacity at net delivered qty so returns free qty for later DNs
		net_qty = flt(dnd.qty) - flt(dnd.returned_qty)

		# If delivered against Sales Invoice
		if dnd.si_detail:
			billed_qty_against_dn = net_qty
			billed_qty_against_so -= billed_qty_against_dn
		else:
			# Get billed qty directly against Delivery Note
			billed_qty_against_dn = get_invoiced_qty_against_dn(dn_detail=dnd.name).get(dnd.name, 0)

		# Distribute qty billed directly against SO between DNs based on FIFO
		if billed_qty_against_so and billed_qty_against_dn < net_qty:
			pending_to_bill = net_qty - billed_qty_against_dn
			if pending_to_bill <= billed_qty_against_so:
				billed_qty_against_dn += pending_to_bill
				billed_qty_against_so -= pending_to_bill
			else:
				billed_qty_against_dn += billed_qty_against_so
				billed_qty_against_so = 0

		qty_map[dnd.name] = flt(billed_qty_against_dn)

	return qty_map
