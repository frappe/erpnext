# Copyright (c) 2026, Aagnya Mistry and contributors
# For license information, please see license.txt

"""GL Entries of investments, posted by Investment Transaction and Investment Interest Accrual."""

import frappe
from frappe.query_builder.functions import Coalesce
from pypika.terms import ValueWrapper

VOUCHER_TYPES = ("Investment Transaction", "Investment Interest Accrual")


def get_investment_gl_query():
	"""GL Entry query joined to the investment voucher that posted each entry."""
	gl_entry = frappe.qb.DocType("GL Entry")
	transaction = frappe.qb.DocType("Investment Transaction")
	accrual = frappe.qb.DocType("Investment Interest Accrual")

	query = (
		frappe.qb.from_(gl_entry)
		.left_join(transaction)
		.on((gl_entry.voucher_type == "Investment Transaction") & (gl_entry.voucher_no == transaction.name))
		.left_join(accrual)
		.on((gl_entry.voucher_type == "Investment Interest Accrual") & (gl_entry.voucher_no == accrual.name))
		.where(gl_entry.voucher_type.isin(VOUCHER_TYPES))
	)

	return frappe._dict(
		query=query,
		gl_entry=gl_entry,
		investment=Coalesce(transaction.investment, accrual.investment),
		transaction_type=Coalesce(transaction.transaction_type, ValueWrapper("Interest Accrual")),
	)
