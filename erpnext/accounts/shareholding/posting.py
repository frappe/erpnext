"""Checks shared by Share Transaction journals."""

import frappe
from frappe import _
from frappe.utils import flt


def money(value, currency):
	from frappe.model.meta import get_field_precision

	precision = get_field_precision(frappe._dict(fieldtype="Currency", precision=None), currency=currency)
	return flt(value, precision)


def assert_journal_unreconciled(transaction):
	if not transaction.journal_entry:
		return
	payment = frappe.qb.DocType("Bank Transaction Payments")
	bank = frappe.qb.DocType("Bank Transaction")
	allocated = (
		frappe.qb.from_(payment)
		.join(bank)
		.on(bank.name == payment.parent)
		.select(payment.name)
		.where(
			(payment.payment_document == "Journal Entry")
			& (payment.payment_entry == transaction.journal_entry)
			& (bank.docstatus == 1)
			& (payment.allocated_amount > 0)
		)
		.limit(1)
	).run()
	if allocated:
		frappe.throw(_("Unreconcile the linked journal before cancelling this Share Transaction."))
