# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Billing status tracking and return invoicing for Delivery Note."""

import frappe
from frappe import _
from frappe.desk.notifications import clear_doctype_notifications
from frappe.query_builder.functions import Sum
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

		if doc.is_return and doc.return_against:
			# A submitted or cancelled return can shift which other returns are settled.
			update_billing_percentage_of_returns(doc.return_against)

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
	"""Qty of each return row that may still be credited: billed on the original row, less earlier credits."""
	original_rows = {d.name: d.dn_detail for d in return_doc.items if d.dn_detail}
	if not original_rows:
		return {}

	billed_qty = get_billed_qty(set(original_rows.values()))
	credited_qty = get_credited_qty(set(original_rows.values()), return_doc.name)
	settled_qty = get_settled_return_qty(return_doc.return_against)
	creditable_qty = {}
	for row in return_doc.items:
		original = original_rows.get(row.name)
		available = flt(billed_qty.get(original)) - flt(credited_qty.get(original))
		unsettled = abs(flt(row.qty)) - flt(settled_qty.get(row.name))
		creditable_qty[row.name] = max(min(unsettled, available), 0)
		credited_qty[original] = flt(credited_qty.get(original)) + creditable_qty[row.name]

	return creditable_qty


def get_billed_qty(original_rows: set) -> dict:
	billed_qty = {}
	for row in frappe.get_all(
		"Delivery Note Item",
		filters={"name": ("in", list(original_rows))},
		fields=["name", "billed_amt", "rate", "qty"],
	):
		billed_qty[row.name] = flt(row.billed_amt) / flt(row.rate) if flt(row.rate) else flt(row.qty)

	return billed_qty


def get_credited_qty(original_rows: set, current_return: str) -> dict:
	return_rows = frappe._dict(
		frappe.get_all(
			"Delivery Note Item",
			filters={
				"dn_detail": ("in", list(original_rows)),
				"docstatus": 1,
				"parent": ("!=", current_return),
			},
			fields=["name", "dn_detail"],
			as_list=True,
		)
	)
	if not return_rows:
		return {}

	sii = frappe.qb.DocType("Sales Invoice Item")
	credited = (
		frappe.qb.from_(sii)
		.select(sii.dn_detail, Sum(sii.qty))
		.where(sii.dn_detail.isin(list(return_rows)) & (sii.docstatus == 1) & (sii.qty < 0))
		.groupby(sii.dn_detail)
	).run()

	credited_qty = {}
	for return_row, qty in credited:
		original = return_rows[return_row]
		credited_qty[original] = flt(credited_qty.get(original)) + abs(flt(qty))

	return credited_qty


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
		.select(dn_item.name, dn_item.dn_detail, dn_item.qty)
		.where(
			(dn.return_against == delivery_note)
			& (dn.is_return == 1)
			& (dn.docstatus == 1)
			& (dn_item.dn_detail.isnotnull())
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
			fields=["name", "qty", "so_detail"],
		)
	}
	invoiced_qty = get_invoiced_qty_against_dn(delivery_note=delivery_note)
	so_details = {row.so_detail for row in original_rows.values() if row.so_detail}
	so_billed = set(
		frappe.get_all(
			"Sales Invoice Item",
			filters={"so_detail": ("in", list(so_details)), "dn_detail": ("is", "not set"), "docstatus": 1},
			pluck="so_detail",
		)
		if so_details
		else []
	)
	returned_qty = {}
	for row in return_rows:
		returned_qty[row.dn_detail] = flt(returned_qty.get(row.dn_detail)) + abs(flt(row.qty))

	qty_precision = frappe.get_precision("Delivery Note Item", "qty")
	settleable_qty = {}
	for original, returned in returned_qty.items():
		returned = flt(returned, qty_precision)
		net_invoiced = flt(invoiced_qty.get(original))
		uninvoiced = flt(flt(original_rows[original].qty) - net_invoiced, qty_precision)
		# Until the net qty is fully invoiced, the next invoice still deducts the returns.
		# Rows also invoiced through the Sales Order stay unsettled.
		fully_invoiced = (
			net_invoiced > 0 and returned >= uninvoiced and original_rows[original].so_detail not in so_billed
		)
		settleable_qty[original] = max(min(returned, uninvoiced), 0) if fully_invoiced else 0

	settled_qty = {}
	for row in return_rows:
		settled = min(abs(flt(row.qty)), settleable_qty[row.dn_detail])
		settleable_qty[row.dn_detail] -= settled
		settled_qty[row.name] = settled

	return settled_qty


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
