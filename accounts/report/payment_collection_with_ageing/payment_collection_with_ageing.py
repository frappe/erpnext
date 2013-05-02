# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
from webnotes import msgprint, _
from accounts.report.accounts_receivable.accounts_receivable import get_ageing_data

def execute(filters=None):
	if not filters: filters = {}
	
	columns = get_columns()
	entries = get_entries(filters)
	si_posting_date_map = get_si_posting_date_map()
	
	data = []
	for d in entries:
		against_invoice_date = d.against_invoice and si_posting_date_map[d.against_invoice] or ""
		
		row = [d.name, d.account, d.posting_date, d.against_invoice, against_invoice_date, 
			d.debit, d.credit, d.cheque_no, d.cheque_date, d.remark]
			
		if d.against_invoice:
			row += get_ageing_data(against_invoice_date, d.posting_date, d.credit or -1*d.debit)
		else:
			row += ["", "", "", "", ""]
			
		data.append(row)
	
	return columns, data
	
def get_columns():
	return ["Journal Voucher:Link/Journal Voucher:140", "Account:Link/Account:140", 
		"Posting Date:Date:100", "Against Invoice:Link/Sales Invoice:130", 
		"Against Invoice Posting Date:Date:130", "Debit:Currency:120", "Credit:Currency:120", 
		"Reference No::100", "Reference Date:Date:100", "Remarks::150", "Age:Int:40", 
		"0-30:Currency:100", "30-60:Currency:100", "60-90:Currency:100", "90-Above:Currency:100"
	]

def get_conditions(filters):
	conditions = ""
	
	customer_accounts = []
	if filters.get("account"):
		customer_accounts = [filters["account"]]
	else:
		cond = filters.get("company") and (" and company = '%s'" % filters["company"]) or ""
		customer_accounts = webnotes.conn.sql_list("""select name from `tabAccount` 
			where ifnull(master_type, '') = 'Customer' and docstatus < 2 %s""" % cond)
	
	if customer_accounts:
		conditions += " and jvd.account in (%s)" % (", ".join(['%s']*len(customer_accounts)))
	else:
		msgprint(_("No Customer Accounts found. Customer Accounts are identified based on \
			'Master Type' value in account record."), raise_exception=1)
		
	if filters.get("from_date"): conditions += " and jv.posting_date >= '%s'" % filters["from_date"]
	if filters.get("to_date"): conditions += " and jv.posting_date <= '%s'" % filters["to_date"]
	
	return conditions, customer_accounts
	
def get_entries(filters):
	conditions, customer_accounts = get_conditions(filters)
	entries =  webnotes.conn.sql("""select jv.name, jvd.account, jv.posting_date, 
		jvd.against_invoice, jvd.debit, jvd.credit, jv.cheque_no, jv.cheque_date, jv.remark
		from `tabJournal Voucher Detail` jvd, `tabJournal Voucher` jv 
		where jvd.parent = jv.name and jv.docstatus=1 %s order by jv.name DESC""" % 
		(conditions), tuple(customer_accounts), as_dict=1)
		
	return entries
	
def get_si_posting_date_map():
	si_posting_date_map = {}
	for t in webnotes.conn.sql("""select name, posting_date from `tabSales Invoice`"""):
		si_posting_date_map[t[0]] = t[1]
		
	return si_posting_date_map