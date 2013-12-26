# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _, msgprint

def execute(filters=None):
	if not filters: filters = {}
	
	columns = get_columns()
	data = get_entries(filters)
	
	return columns, data
	
def get_columns():
	return ["Journal Voucher:Link/Journal Voucher:140", "Account:Link/Account:140", 
		"Posting Date:Date:100", "Clearance Date:Date:110", "Against Account:Link/Account:200", 
		"Debit:Currency:120", "Credit:Currency:120"
	]

def get_conditions(filters):
	conditions = ""
	if not filters.get("account"):
		msgprint(_("Please select Bank Account"), raise_exception=1)
	else:
		conditions += " and jvd.account = %(account)s"
		
	if filters.get("from_date"): conditions += " and jv.posting_date>=%(from_date)s"
	if filters.get("to_date"): conditions += " and jv.posting_date<=%(to_date)s"
	
	return conditions
	
def get_entries(filters):
	conditions = get_conditions(filters)
	entries =  webnotes.conn.sql("""select jv.name, jvd.account, jv.posting_date, 
		jv.clearance_date, jvd.against_account, jvd.debit, jvd.credit
		from `tabJournal Voucher Detail` jvd, `tabJournal Voucher` jv 
		where jvd.parent = jv.name and jv.docstatus=1 %s
		order by jv.name DESC""" % conditions, filters, as_list=1)
	return entries