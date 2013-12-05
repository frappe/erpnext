# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import getdate, nowdate, flt, cstr
from webnotes import msgprint, _
from accounts.report.accounts_receivable.accounts_receivable import get_ageing_data

def execute(filters=None):
	if not filters: filters = {}
	columns = get_columns()
	entries = get_gl_entries(filters)
	account_supplier = dict(webnotes.conn.sql("""select account.name, supplier.supplier_name
		from `tabAccount` account, `tabSupplier` supplier 
		where account.master_type="Supplier" and supplier.name=account.master_name"""))
	
	entries_after_report_date = [[gle.voucher_type, gle.voucher_no] 
		for gle in get_gl_entries(filters, before_report_date=False)]
	
	account_supplier_type_map = get_account_supplier_type_map()
	pi_map = get_pi_map()

	# Age of the invoice on this date
	age_on = getdate(filters.get("report_date")) > getdate(nowdate()) \
		and nowdate() or filters.get("report_date")

	data = []
	for gle in entries:
		if cstr(gle.against_voucher) == gle.voucher_no or not gle.against_voucher \
				or [gle.against_voucher_type, gle.against_voucher] in entries_after_report_date:
			if gle.voucher_type == "Purchase Invoice":
				pi_info = pi_map.get(gle.voucher_no)
				due_date = pi_info.get("due_date")
				bill_no = pi_info.get("bill_no")
				bill_date = pi_info.get("bill_date")
			else:
				due_date = bill_no = bill_date = ""
		
			invoiced_amount = gle.credit > 0 and gle.credit or 0
			outstanding_amount = get_outstanding_amount(gle, 
				filters.get("report_date") or nowdate())

			if abs(flt(outstanding_amount)) > 0.01:
				paid_amount = invoiced_amount - outstanding_amount
				row = [gle.posting_date, gle.account, account_supplier.get(gle.account, ""),
					gle.voucher_type, gle.voucher_no, 
					gle.remarks, account_supplier_type_map.get(gle.account), due_date, bill_no, 
					bill_date, invoiced_amount, paid_amount, outstanding_amount]
				
				# Ageing
				if filters.get("ageing_based_on") == "Due Date":
					ageing_based_on_date = due_date
				else:
					ageing_based_on_date = gle.posting_date
					
				row += get_ageing_data(age_on, ageing_based_on_date, outstanding_amount)
				data.append(row)
				
	return columns, data
	
def get_columns():
	return [
		"Posting Date:Date:80", "Account:Link/Account:150", "Supplier::150", "Voucher Type::110", 
		"Voucher No::120", "Remarks::150", "Supplier Type:Link/Supplier Type:120", 
		"Due Date:Date:80", "Bill No::80", "Bill Date:Date:80", 
		"Invoiced Amount:Currency:100", "Paid Amount:Currency:100", 
		"Outstanding Amount:Currency:100", "Age:Int:50", "0-30:Currency:100", 
		"30-60:Currency:100", "60-90:Currency:100", "90-Above:Currency:100"
	]
	
def get_gl_entries(filters, before_report_date=True):
	conditions, supplier_accounts = get_conditions(filters, before_report_date)
	gl_entries = []
	gl_entries = webnotes.conn.sql("""select * from `tabGL Entry` 
		where docstatus < 2 %s order by posting_date, account""" % 
		(conditions), tuple(supplier_accounts), as_dict=1)
	return gl_entries
	
def get_conditions(filters, before_report_date=True):
	conditions = ""
	if filters.get("company"):
		conditions += " and company='%s'" % filters["company"]
	
	supplier_accounts = []
	if filters.get("account"):
		supplier_accounts = [filters["account"]]
	else:
		supplier_accounts = webnotes.conn.sql_list("""select name from `tabAccount` 
			where ifnull(master_type, '') = 'Supplier' and docstatus < 2 %s""" % 
			conditions, filters)
	
	if supplier_accounts:
		conditions += " and account in (%s)" % (", ".join(['%s']*len(supplier_accounts)))
	else:
		msgprint(_("No Supplier Accounts found. Supplier Accounts are identified based on \
			'Master Type' value in account record."), raise_exception=1)
		
	if filters.get("report_date"):
		if before_report_date:
			conditions += " and posting_date<='%s'" % filters["report_date"]
		else:
			conditions += " and posting_date>'%s'" % filters["report_date"]
		
	return conditions, supplier_accounts
	
def get_account_supplier_type_map():
	account_supplier_type_map = {}
	for each in webnotes.conn.sql("""select t2.name, t1.supplier_type from `tabSupplier` t1, 
			`tabAccount` t2 where t1.name = t2.master_name group by t2.name"""):
		account_supplier_type_map[each[0]] = each[1]
		
	return account_supplier_type_map
	
def get_pi_map():
	""" get due_date from sales invoice """
	pi_map = {}
	for t in webnotes.conn.sql("""select name, due_date, bill_no, bill_date 
			from `tabPurchase Invoice`""", as_dict=1):
		pi_map[t.name] = t
		
	return pi_map

def get_outstanding_amount(gle, report_date):
	payment_amount = webnotes.conn.sql("""
		select sum(ifnull(debit, 0)) - sum(ifnull(credit, 0)) 
		from `tabGL Entry` 
		where account = %s and posting_date <= %s and against_voucher_type = %s 
		and against_voucher = %s and name != %s""", 
		(gle.account, report_date, gle.voucher_type, gle.voucher_no, gle.name))[0][0]
		
	outstanding_amount = flt(gle.credit) - flt(gle.debit) - flt(payment_amount)
	return outstanding_amount
