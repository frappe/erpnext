# Copyright (c) 2026, Aagnya Mistry and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import cint, flt

import erpnext
from erpnext.treasury.report.utils import add_total_row, get_currency_column

CASH_ACCOUNT_TYPES = ("Bank", "Cash")


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_data(filters):
	balances = get_cash_balances(filters.company, filters.as_on_date)
	if not cint(filters.show_zero_balances):
		balances = [row for row in balances if row.balance or row.balance_in_account_currency]

	set_bank_details(balances)
	currency = erpnext.get_company_currency(filters.company)
	for row in balances:
		row.currency = currency

	add_total_row(balances, ["balance"], "account", currency)
	return balances


def get_cash_balances(company, as_on_date):
	"""Balance of every Bank and Cash account on the date, in account and company currency."""
	gl_entry = frappe.qb.DocType("GL Entry")
	account = frappe.qb.DocType("Account")

	return (
		frappe.qb.from_(gl_entry)
		.join(account)
		.on(gl_entry.account == account.name)
		.select(
			gl_entry.account,
			account.account_type,
			account.account_currency,
			Sum(gl_entry.debit_in_account_currency - gl_entry.credit_in_account_currency).as_(
				"balance_in_account_currency"
			),
			Sum(gl_entry.debit - gl_entry.credit).as_("balance"),
		)
		.where(account.account_type.isin(CASH_ACCOUNT_TYPES))
		.where(gl_entry.company == company)
		.where(gl_entry.is_cancelled == 0)
		.where(gl_entry.posting_date <= as_on_date)
		.groupby(gl_entry.account, account.account_type, account.account_currency)
		.orderby(account.account_type)
		.orderby(gl_entry.account)
	).run(as_dict=True)


def set_bank_details(balances):
	"""Bank and account number from the company's Bank Account records linked to the ledger account."""
	bank_accounts = frappe.get_all(
		"Bank Account",
		filters={"account": ("in", [row.account for row in balances]), "is_company_account": 1},
		fields=["account", "bank", "bank_account_no"],
	)
	details = {bank_account.account: bank_account for bank_account in bank_accounts}

	for row in balances:
		row.bank = details.get(row.account, {}).get("bank")
		row.bank_account_no = details.get(row.account, {}).get("bank_account_no")
		row.balance_in_account_currency = flt(row.balance_in_account_currency)


def get_columns():
	return [
		{
			"label": _("Account"),
			"fieldname": "account",
			"fieldtype": "Link",
			"options": "Account",
			"width": 220,
		},
		{"label": _("Account Type"), "fieldname": "account_type", "fieldtype": "Data", "width": 100},
		{"label": _("Bank"), "fieldname": "bank", "fieldtype": "Link", "options": "Bank", "width": 150},
		{"label": _("Bank Account No"), "fieldname": "bank_account_no", "fieldtype": "Data", "width": 150},
		{
			"label": _("Account Currency"),
			"fieldname": "account_currency",
			"fieldtype": "Link",
			"options": "Currency",
			"width": 90,
		},
		{
			"label": _("Balance (Account Currency)"),
			"fieldname": "balance_in_account_currency",
			"fieldtype": "Currency",
			"options": "account_currency",
			"width": 170,
		},
		get_currency_column(_("Balance (Company Currency)"), "balance", 170),
	]
