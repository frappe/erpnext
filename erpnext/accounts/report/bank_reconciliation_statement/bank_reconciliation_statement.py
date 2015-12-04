# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _

def execute(filters=None):
	if not filters: filters = {}

	columns = get_columns()

	if not filters.get("account"): return columns, []
	
	account_currency = frappe.db.get_value("Account", filters.account, "account_currency")

	data = get_entries(filters)
	
	from erpnext.accounts.utils import get_balance_on
	balance_as_per_system = get_balance_on(filters["account"], filters["report_date"])

	total_debit, total_credit = 0,0
	for d in data:
		total_debit += flt(d.debit)
		total_credit += flt(d.credit)

	amounts_not_reflected_in_system = frappe.db.sql("""
		select sum(jvd.debit_in_account_currency - jvd.credit_in_account_currency)
		from `tabJournal Entry Account` jvd, `tabJournal Entry` jv
		where jvd.parent = jv.name and jv.docstatus=1 and jvd.account=%s
		and jv.posting_date > %s and jv.clearance_date <= %s and ifnull(jv.is_opening, 'No') = 'No'
		""", (filters["account"], filters["report_date"], filters["report_date"]))

	amounts_not_reflected_in_system = flt(amounts_not_reflected_in_system[0][0]) \
		if amounts_not_reflected_in_system else 0.0

	bank_bal = flt(balance_as_per_system) - flt(total_debit) + flt(total_credit) \
		+ amounts_not_reflected_in_system

	data += [
		get_balance_row(_("System Balance"), balance_as_per_system, account_currency),
		{},
		{
			"journal_entry": '"' + _("Amounts not reflected in bank") + '"',
			"debit": total_debit,
			"credit": total_credit,
			"account_currency": account_currency
		},
		get_balance_row(_("Amounts not reflected in system"), amounts_not_reflected_in_system, 
			account_currency),
		{},
		get_balance_row(_("Expected balance as per bank"), bank_bal, account_currency)
	]

	return columns, data

def get_columns():
	return [
		{
			"fieldname": "posting_date",
			"label": _("Posting Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "journal_entry",
			"label": _("Journal Entry"),
			"fieldtype": "Link",
			"options": "Journal Entry",
			"width": 220
		},
		{
			"fieldname": "debit",
			"label": _("Debit"),
			"fieldtype": "Currency",
			"options": "account_currency",
			"width": 120
		},
		{
			"fieldname": "credit",
			"label": _("Credit"),
			"fieldtype": "Currency",
			"options": "account_currency",
			"width": 120
		},
		{
			"fieldname": "against_account",
			"label": _("Against Account"),
			"fieldtype": "Link",
			"options": "Account",
			"width": 200
		},
		{
			"fieldname": "reference",
			"label": _("Reference"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "ref_date",
			"label": _("Ref Date"),
			"fieldtype": "Date",
			"width": 110
		},
		{
			"fieldname": "clearance_date",
			"label": _("Clearance Date"),
			"fieldtype": "Date",
			"width": 110
		},		
		{
			"fieldname": "account_currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"width": 100
		}
	]

def get_entries(filters):
	entries = frappe.db.sql("""select
			jv.posting_date, jv.name as journal_entry, jvd.debit_in_account_currency as debit, 
			jvd.credit_in_account_currency as credit, jvd.against_account, 
			jv.cheque_no as reference, jv.cheque_date as ref_date, jv.clearance_date, jvd.account_currency
		from
			`tabJournal Entry Account` jvd, `tabJournal Entry` jv
		where jvd.parent = jv.name and jv.docstatus=1
			and jvd.account = %(account)s and jv.posting_date <= %(report_date)s
			and ifnull(jv.clearance_date, '4000-01-01') > %(report_date)s
			and ifnull(jv.is_opening, 'No') = 'No'
		order by jv.name DESC""", filters, as_dict=1)

	return entries

def get_balance_row(label, amount, account_currency):
	if amount > 0:
		return {
			"journal_entry": '"' + label + '"',
			"debit": amount,
			"credit": 0,
			"account_currency": account_currency
		}
	else:
		return {
			"journal_entry": '"' + label + '"',
			"debit": 0,
			"credit": abs(amount),
			"account_currency": account_currency
		}