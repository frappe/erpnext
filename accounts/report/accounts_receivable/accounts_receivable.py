from __future__ import unicode_literals
import webnotes
from webnotes import msgprint, _
from webnotes.utils import getdate, nowdate, flt, cstr

def execute(filters=None):
	if not filters: filters = {}
	columns = get_columns()
	entries = get_gl_entries(filters)
	account_customer = dict(webnotes.conn.sql("""select account.name, customer.customer_name
		from `tabAccount` account, `tabCustomer` customer 
		where account.master_type="Customer" and customer.name=account.master_name"""))
	
	entries_after_report_date = [[gle.voucher_type, gle.voucher_no] 
		for gle in get_gl_entries(filters, upto_report_date=False)]
	
	account_territory_map = get_account_territory_map()
	si_due_date_map = get_si_due_date_map()
		
	# Age of the invoice on this date
	age_on = getdate(filters.get("report_date")) > getdate(nowdate()) \
		and nowdate() or filters.get("report_date")

	data = []
	for gle in entries:
		if cstr(gle.against_voucher) == gle.voucher_no or not gle.against_voucher \
				or [gle.against_voucher_type, gle.against_voucher] in entries_after_report_date:
			
			due_date = (gle.voucher_type == "Sales Invoice") \
				and si_due_date_map.get(gle.voucher_no) or ""
		
			invoiced_amount = gle.debit > 0 and gle.debit or 0		
			outstanding_amount = get_outstanding_amount(gle, 
				filters.get("report_date") or nowdate())
		
			if abs(flt(outstanding_amount)) > 0.01:
				payment_amount = invoiced_amount - outstanding_amount
				row = [gle.posting_date, gle.account, account_customer.get(gle.account, ""), 
					gle.voucher_type, gle.voucher_no, 
					gle.remarks, due_date, account_territory_map.get(gle.account), 
					invoiced_amount, payment_amount, outstanding_amount]
				# Ageing
				if filters.get("ageing_based_on") == "Due Date":
					ageing_based_on_date = due_date
				else:
					ageing_based_on_date = gle.posting_date
				row += get_ageing_data(ageing_based_on_date, age_on, outstanding_amount)
								
				data.append(row)
								
	return columns, data
	
def get_columns():
	return [
		"Posting Date:Date:80", "Account:Link/Account:150", "Customer::150", "Voucher Type::110", 
		"Voucher No::120", "Remarks::150", "Due Date:Date:80", "Territory:Link/Territory:80", 
		"Invoiced Amount:Currency:100", "Payment Received:Currency:100", 
		"Outstanding Amount:Currency:100", "Age:Int:50", "0-30:Currency:100", 
		"30-60:Currency:100", "60-90:Currency:100", "90-Above:Currency:100"
	]
	
def get_gl_entries(filters, upto_report_date=True):
	conditions, customer_accounts = get_conditions(filters, upto_report_date)
	return webnotes.conn.sql("""select * from `tabGL Entry` 
		where ifnull(is_cancelled, 'No') = 'No' %s order by posting_date, account""" % 
		(conditions), tuple(customer_accounts), as_dict=1)
	
def get_conditions(filters, upto_report_date=True):
	conditions = ""
	if filters.get("company"):
		conditions += " and company='%s'" % filters["company"]
	
	customer_accounts = []
	if filters.get("account"):
		customer_accounts = [filters["account"]]
	else:
		customer_accounts = webnotes.conn.sql_list("""select name from `tabAccount` 
			where ifnull(master_type, '') = 'Customer' and docstatus < 2 %s""" % 
			conditions, filters)
	
	if customer_accounts:
		conditions += " and account in (%s)" % (", ".join(['%s']*len(customer_accounts)))
	else:
		msgprint(_("No Customer Accounts found. Customer Accounts are identified based on \
			'Master Type' value in account record."), raise_exception=1)
		
	if filters.get("report_date"):
		if upto_report_date:
			conditions += " and posting_date<='%s'" % filters["report_date"]
		else:
			conditions += " and posting_date>'%s'" % filters["report_date"]
		
	return conditions, customer_accounts
	
def get_account_territory_map():
	account_territory_map = {}
	for each in webnotes.conn.sql("""select t2.name, t1.territory from `tabCustomer` t1, 
			`tabAccount` t2 where t1.name = t2.master_name"""):
		account_territory_map[each[0]] = each[1]
		
	return account_territory_map
	
def get_si_due_date_map():
	""" get due_date from sales invoice """
	si_due_date_map = {}
	for t in webnotes.conn.sql("""select name, due_date from `tabSales Invoice`"""):
		si_due_date_map[t[0]] = t[1]
		
	return si_due_date_map

def get_outstanding_amount(gle, report_date):
	payment_amount = webnotes.conn.sql("""
		select sum(ifnull(credit, 0)) - sum(ifnull(debit, 0)) 
		from `tabGL Entry` 
		where account = %s and posting_date <= %s and against_voucher_type = %s 
		and against_voucher = %s and name != %s and ifnull(is_cancelled, 'No') = 'No'""", 
		(gle.account, report_date, gle.voucher_type, gle.voucher_no, gle.name))[0][0]
		
	return flt(gle.debit) - flt(gle.credit) - flt(payment_amount)

def get_payment_amount(gle, report_date, entries_after_report_date):
	payment_amount = 0
	if flt(gle.credit) > 0 and (not gle.against_voucher or 
		[gle.against_voucher_type, gle.against_voucher] in entries_after_report_date):
			payment_amount = gle.credit
	elif flt(gle.debit) > 0:
		payment_amount = webnotes.conn.sql("""
			select sum(ifnull(credit, 0)) - sum(ifnull(debit, 0)) from `tabGL Entry` 
			where account = %s and posting_date <= %s and against_voucher_type = %s 
			and against_voucher = %s and name != %s and ifnull(is_cancelled, 'No') = 'No'""", 
			(gle.account, report_date, gle.voucher_type, gle.voucher_no, gle.name))[0][0]
	
	return flt(payment_amount)

def get_ageing_data(ageing_based_on_date, age_on, outstanding_amount):
	val1 = val2 = val3 = val4 = diff = 0
	diff = age_on and ageing_based_on_date \
		and (getdate(age_on) - getdate(ageing_based_on_date)).days or 0

	if diff <= 30:
		val1 = outstanding_amount
	elif 30 < diff <= 60:
		val2 = outstanding_amount
	elif 60 < diff <= 90:
		val3 = outstanding_amount
	elif diff > 90:
		val4 = outstanding_amount
		
	return [diff, val1, val2, val3, val4]