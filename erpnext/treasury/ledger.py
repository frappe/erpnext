# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""GL Entries of investments, posted by Investment Transaction, Investment Interest Accrual
and (when asked for) Investment Revaluation."""

import frappe
from frappe.query_builder import Case
from frappe.query_builder.functions import Coalesce

VOUCHER_TYPES = ("Investment Transaction", "Investment Interest Accrual")


def get_investment_gl_query(include_revaluations=False):
	"""GL Entry query joined to the investment voucher that posted each entry.

	Revaluations post one row per investment, so their entries are matched through the row.
	"""
	gl_entry = frappe.qb.DocType("GL Entry")
	transaction = frappe.qb.DocType("Investment Transaction")
	accrual = frappe.qb.DocType("Investment Interest Accrual")
	revaluation_row = frappe.qb.DocType("Investment Revaluation Detail")
	voucher_types = (*VOUCHER_TYPES, "Investment Revaluation") if include_revaluations else VOUCHER_TYPES

	query = (
		frappe.qb.from_(gl_entry)
		.left_join(transaction)
		.on((gl_entry.voucher_type == "Investment Transaction") & (gl_entry.voucher_no == transaction.name))
		.left_join(accrual)
		.on((gl_entry.voucher_type == "Investment Interest Accrual") & (gl_entry.voucher_no == accrual.name))
		.left_join(revaluation_row)
		.on(
			(gl_entry.voucher_type == "Investment Revaluation")
			& (gl_entry.voucher_detail_no == revaluation_row.name)
		)
		.where(gl_entry.voucher_type.isin(voucher_types))
	)

	return frappe._dict(
		query=query,
		gl_entry=gl_entry,
		investment=Coalesce(transaction.investment, accrual.investment, revaluation_row.investment),
		transaction_type=Coalesce(
			transaction.transaction_type,
			Case().when(accrual.name.isnotnull(), "Interest Accrual").else_("Revaluation"),
		),
	)
