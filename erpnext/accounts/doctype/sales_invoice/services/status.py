# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Status computation and display helpers for Sales Invoice."""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate


class StatusService:
	def __init__(self, doc):
		self.doc = doc

	def set_status(
		self, update: bool = False, status: str | None = None, update_modified: bool = True
	) -> None:
		doc = self.doc
		if doc.is_new():
			if doc.get("amended_from"):
				doc.status = "Draft"
			return

		outstanding_amount = flt(doc.outstanding_amount, doc.precision("outstanding_amount"))
		total = get_total_in_party_account_currency(doc)

		if not status:
			if doc.docstatus == 2:
				status = "Cancelled"
			elif doc.docstatus == 1:
				if doc.is_internal_transfer():
					doc.status = "Internal Transfer"
				elif is_overdue(doc, total):
					doc.status = "Overdue"
				elif 0 < outstanding_amount < total:
					doc.status = "Partly Paid"
				elif outstanding_amount > 0 and getdate(doc.due_date) >= getdate():
					doc.status = "Unpaid"
				elif doc.is_return == 0 and frappe.db.get_value(
					"Sales Invoice", {"is_return": 1, "return_against": doc.name, "docstatus": 1}
				):
					doc.status = "Credit Note Issued"
				elif doc.is_return == 1:
					doc.status = "Return"
				elif outstanding_amount <= 0:
					doc.status = "Paid"
				else:
					doc.status = "Submitted"

				if (
					doc.status in ("Unpaid", "Partly Paid", "Overdue")
					and doc.is_discounted
					and get_discounting_status(doc.name) == "Disbursed"
				):
					doc.status += " and Discounted"

			else:
				doc.status = "Draft"

		if update:
			doc.db_set("status", doc.status, update_modified=update_modified)

	def set_indicator(self) -> None:
		doc = self.doc
		if doc.outstanding_amount < 0:
			doc.indicator_title = _("Credit Note Issued")
			doc.indicator_color = "gray"
		elif doc.outstanding_amount > 0 and getdate(doc.due_date) >= getdate(nowdate()):
			doc.indicator_color = "orange"
			doc.indicator_title = _("Unpaid")
		elif doc.outstanding_amount > 0 and getdate(doc.due_date) < getdate(nowdate()):
			doc.indicator_color = "red"
			doc.indicator_title = _("Overdue")
		elif cint(doc.is_return) == 1:
			doc.indicator_title = _("Return")
			doc.indicator_color = "gray"
		else:
			doc.indicator_color = "green"
			doc.indicator_title = _("Paid")


def get_total_in_party_account_currency(doc) -> float:
	total_fieldname = "grand_total" if doc.disable_rounded_total else "rounded_total"
	if doc.party_account_currency != doc.currency:
		total_fieldname = "base_" + total_fieldname
	return flt(doc.get(total_fieldname), doc.precision(total_fieldname))


def is_overdue(doc, total: float) -> bool | None:
	outstanding_amount = flt(doc.outstanding_amount, doc.precision("outstanding_amount"))
	if outstanding_amount <= 0:
		return

	today = getdate()
	if doc.get("is_pos") or not doc.get("payment_schedule"):
		return getdate(doc.due_date) < today

	payment_amount_field = (
		"base_payment_amount" if doc.party_account_currency != doc.currency else "payment_amount"
	)
	payable_amount = flt(
		sum(
			payment.get(payment_amount_field)
			for payment in doc.payment_schedule
			if getdate(payment.due_date) < today
		),
		doc.precision("outstanding_amount"),
	)
	return flt(total - outstanding_amount, doc.precision("outstanding_amount")) < payable_amount


def get_discounting_status(sales_invoice: str) -> str | None:
	status = None

	InvoiceDiscounting = frappe.qb.DocType("Invoice Discounting")
	DiscountedInvoice = frappe.qb.DocType("Discounted Invoice")

	query = (
		frappe.qb.from_(InvoiceDiscounting)
		.join(DiscountedInvoice)
		.on(InvoiceDiscounting.name == DiscountedInvoice.parent)
		.select(InvoiceDiscounting.status)
		.where(DiscountedInvoice.sales_invoice == sales_invoice)
		.where(InvoiceDiscounting.docstatus == 1)
		.where(InvoiceDiscounting.status.isin(["Disbursed", "Settled"]))
	)

	invoice_discounting_list = query.run()

	for d in invoice_discounting_list:
		status = d[0]
		if status == "Disbursed":
			break
	return status
