# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE


import frappe

from erpnext.accounts.doctype.account_closing_balance.account_closing_balance import (
	make_closing_entries,
)
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.utils import get_fiscal_year


def execute():
	frappe.db.truncate("Account Closing Balance")

	gle_fields = get_gle_fields()

	for company in frappe.get_all("Company", pluck="name"):
		i = 0
		company_wise_order = {}
		for pcv in get_period_closing_vouchers(company):
			company_wise_order.setdefault(pcv.company, [])
			if pcv.period_end_date not in company_wise_order[pcv.company]:
				pcv_doc = frappe.get_doc("Period Closing Voucher", pcv.name)
				pcv_doc.pl_accounts_reverse_gle = get_pcv_gl_entries_for_pl_accounts(pcv, gle_fields)
				pcv_doc.closing_account_gle = get_pcv_gl_entries_for_closing_accounts(pcv, gle_fields)
				closing_entries = pcv_doc.get_account_closing_balances()
				make_closing_entries(closing_entries, pcv.name, pcv.company, pcv.period_end_date)

				company_wise_order[pcv.company].append(pcv.period_end_date)
				i += 1


def get_gle_fields():
	default_diemnsion_fields = ["cost_center", "finance_book", "project"]
	accounting_dimension_fields = get_accounting_dimensions()
	gle_fields = [
		"name",
		"company",
		"posting_date",
		"account",
		"account_currency",
		"debit",
		"credit",
		"debit_in_account_currency",
		"credit_in_account_currency",
		*default_diemnsion_fields,
		*accounting_dimension_fields,
	]

	return gle_fields


def get_period_closing_vouchers(company):
	return frappe.db.get_all(
		"Period Closing Voucher",
		fields=["name", "closing_account_head", "period_start_date", "period_end_date", "company"],
		filters={"docstatus": 1, "company": company},
		order_by="period_end_date",
	)


def get_pcv_gl_entries_for_pl_accounts(pcv, gle_fields):
	return get_gl_entries(pcv, gle_fields, {"account": ["!=", pcv.closing_account_head]})


def get_pcv_gl_entries_for_closing_accounts(pcv, gle_fields):
	return get_gl_entries(pcv, gle_fields, {"account": pcv.closing_account_head})


def get_gl_entries(pcv, gle_fields, accounts_filter=None):
	filters = {"voucher_no": pcv.name, "is_cancelled": 0}
	if accounts_filter:
		filters.update(accounts_filter)

	gl_entries = frappe.db.get_all(
		"GL Entry",
		filters=filters,
		fields=gle_fields,
	)
	for entry in gl_entries:
		entry["is_period_closing_voucher_entry"] = 1
		entry["closing_date"] = pcv.period_end_date
		entry["period_closing_voucher"] = pcv.name

	return gl_entries
