# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _

def execute(filters=None):
	if not filters: filters = {}

	columns = get_columns()

	if not filters.get("account"): return columns, []

	data = get_entries(filters)

	from erpnext.accounts.utils import get_balance_on
	balance_as_per_system = get_balance_on(filters["account"], filters["report_date"])

	total_debit, total_credit = 0,0
	for d in data:
		total_debit += flt(d[2])
		total_credit += flt(d[3])

	amounts_not_reflected_in_system = frappe.db.sql("""select sum(ifnull(jvd.debit, 0) - ifnull(jvd.credit, 0))
		from `tabJournal Voucher Detail` jvd, `tabJournal Voucher` jv
		where jvd.parent = jv.name and jv.docstatus=1 and jvd.account=%s
		and jv.posting_date > %s and jv.clearance_date <= %s
		""", (filters["account"], filters["report_date"], filters["report_date"]))

	amounts_not_reflected_in_system = flt(amounts_not_reflected_in_system[0][0]) \
		if amounts_not_reflected_in_system else 0.0

	bank_bal = flt(balance_as_per_system) - flt(total_debit) + flt(total_credit) \
		+ amounts_not_reflected_in_system

	data += [
		get_balance_row(_("System Balance"), balance_as_per_system),
		[""]*len(columns),
		["", _("Amounts not reflected in bank"), total_debit, total_credit, "", "", "", ""],
		get_balance_row(_("Amounts not reflected in system"), amounts_not_reflected_in_system),
		[""]*len(columns),
		get_balance_row(_("Expected balance as per bank"), bank_bal)
	]

	return columns, data

def get_columns():
	return ["Posting Date:Date:100", "Journal Voucher:Link/Journal Voucher:220",
		"Debit:Currency:120", "Credit:Currency:120",
		"Against Account:Link/Account:200", "Reference::100", "Ref Date:Date:110", "Clearance Date:Date:110"
	]

def get_entries(filters):
	entries = frappe.db.sql("""select
			jv.posting_date, jv.name, jvd.debit, jvd.credit,
			jvd.against_account, jv.cheque_no, jv.cheque_date, jv.clearance_date
		from
			`tabJournal Voucher Detail` jvd, `tabJournal Voucher` jv
		where jvd.parent = jv.name and jv.docstatus=1
			and jvd.account = %(account)s and jv.posting_date <= %(report_date)s
			and ifnull(jv.clearance_date, '4000-01-01') > %(report_date)s
		order by jv.name DESC""", filters, as_list=1)

	return entries

def get_balance_row(label, amount):
	if amount > 0:
		return ["", label, amount, 0, "", "", "", ""]
	else:
		return ["", label, 0, abs(amount), "", "", "", ""]
