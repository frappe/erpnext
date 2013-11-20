# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _, msgprint
from webnotes.utils import flt

def execute(filters=None):
	if not filters: filters = {}
		
	columns = get_columns()	
	data = get_entries(filters)
	
	from accounts.utils import get_balance_on
	balance_as_per_company = get_balance_on(filters["account"], filters["report_date"])

	total_debit, total_credit = 0,0
	for d in data:
		total_debit += flt(d[4])
		total_credit += flt(d[5])

	if webnotes.conn.get_value("Account", filters["account"], "debit_or_credit") == 'Debit':
		bank_bal = flt(balance_as_per_company) - flt(total_debit) + flt(total_credit)
	else:
		bank_bal = flt(balance_as_per_company) + flt(total_debit) - flt(total_credit)
		
	data += [
		["", "", "", "Balance as per company books", balance_as_per_company, ""], 
		["", "", "", "Amounts not reflected in bank", total_debit, total_credit], 
		["", "", "", "Balance as per bank", bank_bal, ""]
	]
			
	return columns, data
	
	
def get_columns():
	return ["Journal Voucher:Link/Journal Voucher:140", "Posting Date:Date:100", 
		"Clearance Date:Date:110", "Against Account:Link/Account:200", 
		"Debit:Currency:120", "Credit:Currency:120"
	]

def get_conditions(filters):
	conditions = ""
	if not filters.get("account"):
		msgprint(_("Please select Bank Account"), raise_exception=1)
	else:
		conditions += " and jvd.account = %(account)s"
		
	if not filters.get("report_date"):
		msgprint(_("Please select Date on which you want to run the report"), raise_exception=1)
	else:
		conditions += """ and jv.posting_date <= %(report_date)s 
			and ifnull(jv.clearance_date, '4000-01-01') > %(report_date)s"""

	return conditions
	
def get_entries(filters):
	conditions = get_conditions(filters)
	entries = webnotes.conn.sql("""select jv.name, jv.posting_date, jv.clearance_date, 
		jvd.against_account, jvd.debit, jvd.credit
		from `tabJournal Voucher Detail` jvd, `tabJournal Voucher` jv 
		where jvd.parent = jv.name and jv.docstatus=1 and ifnull(jv.cheque_no, '')!= '' %s
		order by jv.name DESC""" % conditions, filters, as_list=1)
		
	return entries