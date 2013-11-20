# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import msgprint, _
from accounts.report.accounts_receivable.accounts_receivable import get_ageing_data

def execute(filters=None):
	if not filters: filters = {}
	
	columns = get_columns()
	entries = get_entries(filters)
	pi_posting_date_map = get_pi_posting_date_map()
	
	data = []
	for d in entries:
		against_voucher_date = d.against_voucher and pi_posting_date_map[d.against_voucher] or ""
		
		row = [d.name, d.account, d.posting_date, d.against_voucher, against_voucher_date, 
			d.debit, d.credit, d.cheque_no, d.cheque_date, d.remark]
			
		if d.against_voucher:
			row += get_ageing_data(against_voucher_date, d.posting_date, d.debit or -1*d.credit)
		else:
			row += ["", "", "", "", ""]
			
		data.append(row)
	
	return columns, data
	
def get_columns():
	return ["Journal Voucher:Link/Journal Voucher:140", "Account:Link/Account:140", 
		"Posting Date:Date:100", "Against Invoice:Link/Purchase Invoice:130", 
		"Against Invoice Posting Date:Date:130", "Debit:Currency:120", "Credit:Currency:120", 
		"Reference No::100", "Reference Date:Date:100", "Remarks::150", "Age:Int:40", 
		"0-30:Currency:100", "30-60:Currency:100", "60-90:Currency:100", "90-Above:Currency:100"
	]

def get_conditions(filters):
	conditions = ""
	supplier_accounts = []
	if filters.get("account"):
		supplier_accounts = [filters["account"]]
	else:
		cond = filters.get("company") and (" and company = '%s'" % filters["company"]) or ""
		supplier_accounts = webnotes.conn.sql_list("""select name from `tabAccount` 
			where ifnull(master_type, '') = 'Supplier' and docstatus < 2 %s""" % cond)
	
	if supplier_accounts:
		conditions += " and jvd.account in (%s)" % (", ".join(['%s']*len(supplier_accounts)))
	else:
		msgprint(_("No Supplier Accounts found. Supplier Accounts are identified based on \
			'Master Type' value in account record."), raise_exception=1)
		
	if filters.get("from_date"): conditions += " and jv.posting_date >= '%s'" % filters["from_date"]
	if filters.get("to_date"): conditions += " and jv.posting_date <= '%s'" % filters["to_date"]

	return conditions, supplier_accounts
	
def get_entries(filters):
	conditions, supplier_accounts = get_conditions(filters)
	entries =  webnotes.conn.sql("""select jv.name, jvd.account, jv.posting_date, 
		jvd.against_voucher, jvd.debit, jvd.credit, jv.cheque_no, jv.cheque_date, jv.remark
		from `tabJournal Voucher Detail` jvd, `tabJournal Voucher` jv 
		where jvd.parent = jv.name and jv.docstatus=1 %s order by jv.name DESC""" % 
		(conditions), tuple(supplier_accounts), as_dict=1)
		
	return entries
	
def get_pi_posting_date_map():
	pi_posting_date_map = {}
	for t in webnotes.conn.sql("""select name, posting_date from `tabPurchase Invoice`"""):
		pi_posting_date_map[t[0]] = t[1]
		
	return pi_posting_date_map