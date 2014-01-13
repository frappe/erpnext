# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import flt

def execute(filters=None):
	if not filters: filters = {}
	
	debit_or_credit = webnotes.conn.get_value("Account", filters["account"], "debit_or_credit")
	
	columns = get_columns()
	data = get_entries(filters)
	
	from accounts.utils import get_balance_on
	balance_as_per_company = get_balance_on(filters["account"], filters["report_date"])

	total_debit, total_credit = 0,0
	for d in data:
		total_debit += flt(d[4])
		total_credit += flt(d[5])

	if debit_or_credit == 'Debit':
		bank_bal = flt(balance_as_per_company) - flt(total_debit) + flt(total_credit)
	else:
		bank_bal = flt(balance_as_per_company) + flt(total_debit) - flt(total_credit)
		
	data += [
		get_balance_row("Balance as per company books", balance_as_per_company, debit_or_credit),
		["", "", "", "Amounts not reflected in bank", total_debit, total_credit], 
		get_balance_row("Balance as per bank", bank_bal, debit_or_credit)
	]
	
	return columns, data
	
def get_columns():
	return ["Journal Voucher:Link/Journal Voucher:140", "Posting Date:Date:100", 
		"Clearance Date:Date:110", "Against Account:Link/Account:200", 
		"Debit:Currency:120", "Credit:Currency:120"
	]
	
def get_entries(filters):
	entries = webnotes.conn.sql("""select 
			jv.name, jv.posting_date, jv.clearance_date, jvd.against_account, jvd.debit, jvd.credit
		from 
			`tabJournal Voucher Detail` jvd, `tabJournal Voucher` jv 
		where jvd.parent = jv.name and jv.docstatus=1 and ifnull(jv.cheque_no, '')!= '' 
			and jvd.account = %(account)s and jv.posting_date <= %(report_date)s 
			and ifnull(jv.clearance_date, '4000-01-01') > %(report_date)s
		order by jv.name DESC""", filters, as_list=1)
		
	return entries
	
def get_balance_row(label, amount, debit_or_credit):
	if debit_or_credit == "Debit":
		return ["", "", "", label, amount, 0]
	else:
		return ["", "", "", label, 0, amount]