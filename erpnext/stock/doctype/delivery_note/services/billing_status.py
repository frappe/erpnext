# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Billing status tracking and return invoicing for Delivery Note."""

import frappe
from frappe import _
from frappe.desk.notifications import clear_doctype_notifications
from frappe.query_builder.functions import Sum
from frappe.utils import flt


class BillingStatusService:
	def __init__(self, doc):
		self.doc = doc

	def update_status(self, status: str) -> None:
		doc = self.doc
		doc.set_status(update=True, status=status)
		doc.notify_update()
		clear_doctype_notifications(doc)

	def update_billing_status(self, update_modified: bool = True) -> None:
		doc = self.doc
		updated_delivery_notes = [doc.name]
		for d in doc.get("items"):
			if d.si_detail and not d.so_detail:
				d.db_set("billed_amt", d.amount, update_modified=update_modified)
			elif d.so_detail:
				updated_delivery_notes += update_billed_amount_based_on_so(d.so_detail, update_modified)

		for dn in set(updated_delivery_notes):
			dn_doc = doc if (dn == doc.name) else frappe.get_lazy_doc("Delivery Note", dn)
			dn_doc.update_billing_percentage(update_modified=update_modified)

		doc.load_from_db()

	def make_return_invoice(self) -> None:
		from erpnext.stock.doctype.delivery_note.mapper import make_sales_invoice

		try:
			return_invoice = make_sales_invoice(self.doc.name)
			return_invoice.is_return = True
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
			billed_amt_against_dn = frappe.db.sql(
				"""select sum(amount) from `tabSales Invoice Item`
				where dn_detail=%s and docstatus=1""",
				dnd.name,
			)
			billed_amt_against_dn = billed_amt_against_dn and billed_amt_against_dn[0][0] or 0

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
