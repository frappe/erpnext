"""Checks shared by Share Transaction journals."""

import frappe
from frappe import _
from frappe.utils import flt


def money(value, currency):
	from frappe.model.meta import get_field_precision

	precision = get_field_precision(frappe._dict(fieldtype="Currency", precision=None), currency=currency)
	return flt(value, precision)


def assert_journal_unreconciled(transaction):
	if transaction.journal_entry and frappe.db.exists(
		"Bank Transaction Payments",
		{"payment_document": "Journal Entry", "payment_entry": transaction.journal_entry},
	):
		frappe.throw(_("Unreconcile the linked journal before cancelling this Share Transaction."))
