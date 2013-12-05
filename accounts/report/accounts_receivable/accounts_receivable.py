# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _
from webnotes.utils import getdate, nowdate, flt

class AccountsReceivableReport(object):
	def __init__(self, filters=None):
		self.filters = webnotes._dict(filters or {})
		self.filters.report_date = getdate(self.filters.report_date or nowdate())
		self.age_as_on = getdate(nowdate()) \
			if self.filters.report_date > getdate(nowdate()) \
			else self.filters.report_date
			
	def run(self):
		return self.get_columns(), self.get_data()
		
	def get_columns(self):
		return [
			"Posting Date:Date:80", "Account:Link/Account:150",
			"Voucher Type::110", "Voucher No::120", "::30",
			"Due Date:Date:80",  
			"Invoiced Amount:Currency:100", "Payment Received:Currency:100", 
			"Outstanding Amount:Currency:100", "Age:Int:50", "0-30:Currency:100",
			"30-60:Currency:100", "60-90:Currency:100", "90-Above:Currency:100",
			"Customer:Link/Customer:200", "Territory:Link/Territory:80", "Remarks::200"
		]
		
	def get_data(self):
		data = []
		future_vouchers = self.get_entries_after(self.filters.report_date)
		for gle in self.get_entries_till(self.filters.report_date):
			if self.is_receivable(gle, future_vouchers):
				outstanding_amount = self.get_outstanding_amount(gle, self.filters.report_date)
				if abs(outstanding_amount) > 0.01:
					due_date = self.get_due_date(gle)
					invoiced_amount = gle.debit if (gle.debit > 0) else 0
					payment_received = invoiced_amount - outstanding_amount
					row = [gle.posting_date, gle.account,
						gle.voucher_type, gle.voucher_no, due_date,
						invoiced_amount, payment_received,
						outstanding_amount]
					entry_date = due_date if self.filters.ageing_based_on=="Due Date" \
						else gle.posting_date
					row += get_ageing_data(self.age_as_on, entry_date, outstanding_amount)
					row += [self.get_customer(gle.account), self.get_territory(gle.account), gle.remarks]
					data.append(row)
		
		for i in range(0,len(data)):
			data[i].insert(4, """<a href="%s"><i class="icon icon-share" style="cursor: pointer;"></i></a>""" \
				% ("/".join(["#Form", data[i][2], data[i][3]]),))
		
		return data
				
	def get_entries_after(self, report_date):
		# returns a distinct list
		return list(set([(e.voucher_type, e.voucher_no) for e in self.get_gl_entries()
			if getdate(e.posting_date) > report_date]))
			
	def get_entries_till(self, report_date):
		# returns a generator
		return (e for e in self.get_gl_entries() 
			if getdate(e.posting_date) <= report_date)
			
	def is_receivable(self, gle, future_vouchers):
		return ((not gle.against_voucher) or (gle.against_voucher==gle.voucher_no) or 
			((gle.against_voucher_type, gle.against_voucher) in future_vouchers))
			
	def get_outstanding_amount(self, gle, report_date):
		payment_received = 0.0
		for e in self.get_gl_entries_for(gle.account, gle.voucher_type, gle.voucher_no):
			if getdate(e.posting_date) <= report_date and e.name!=gle.name:
				payment_received += (flt(e.credit) - flt(e.debit))
					
		return flt(gle.debit) - flt(gle.credit) - payment_received
		
	def get_customer(self, account):
		return self.get_account_map().get(account).get("customer_name") or ""
		
	def get_territory(self, account):
		return self.get_account_map().get(account).get("territory") or ""
		
	def get_account_map(self):
		if not hasattr(self, "account_map"):
			self.account_map = dict(((r.name, r) for r in webnotes.conn.sql("""select 
				account.name, customer.customer_name, customer.territory
				from `tabAccount` account, `tabCustomer` customer 
				where account.master_type="Customer" 
				and customer.name=account.master_name""", as_dict=True)))
				
		return self.account_map
		
	def get_due_date(self, gle):
		if not hasattr(self, "invoice_due_date_map"):
			# TODO can be restricted to posting date
			self.invoice_due_date_map = dict(webnotes.conn.sql("""select name, due_date
				from `tabSales Invoice` where docstatus=1"""))
				
		return gle.voucher_type == "Sales Invoice" \
			and self.invoice_due_date_map.get(gle.voucher_no) or ""
		
	def get_gl_entries(self):
		if not hasattr(self, "gl_entries"):
			conditions, values = self.prepare_conditions()
			self.gl_entries = webnotes.conn.sql("""select * from `tabGL Entry`
				where docstatus < 2 {} order by posting_date, account""".format(conditions),
				values, as_dict=True)
				
		return self.gl_entries
		
	def prepare_conditions(self):
		conditions = [""]
		values = {}
		
		if self.filters.company:
			conditions.append("company=%(company)s")
			values["company"] = self.filters.company
		
		if self.filters.account:
			conditions.append("account=%(account)s")
			values["account"] = self.filters.account
		else:
			account_map = self.get_account_map()
			if not account_map:
				webnotes.throw(_("No Customer Accounts found."))
			else:
				accounts_list = ['"{}"'.format(ac) for ac in account_map]
				conditions.append("account in ({})".format(", ".join(accounts_list)))
		
		return " and ".join(conditions), values
		
	def get_gl_entries_for(self, account, against_voucher_type, against_voucher):
		if not hasattr(self, "gl_entries_map"):
			self.gl_entries_map = {}
			for gle in self.get_gl_entries():
				if gle.against_voucher_type and gle.against_voucher:
					self.gl_entries_map.setdefault(gle.account, {})\
						.setdefault(gle.against_voucher_type, {})\
						.setdefault(gle.against_voucher, [])\
						.append(gle)
		
		return self.gl_entries_map.get(account, {})\
			.get(against_voucher_type, {})\
			.get(against_voucher, [])

def execute(filters=None):
	return AccountsReceivableReport(filters).run()
	
def get_ageing_data(age_as_on, entry_date, outstanding_amount):
	# [0-30, 30-60, 60-90, 90-above]
	outstanding_range = [0.0, 0.0, 0.0, 0.0]
	if not (age_as_on and entry_date):
		return [0] + outstanding_range
		
	age = (getdate(age_as_on) - getdate(entry_date)).days or 0
	index = None
	for i, days in enumerate([30, 60, 90]):
		if age <= days:
			index = i
			break
	
	if index is None: index = 3
	outstanding_range[index] = outstanding_amount
	
	return [age] + outstanding_range
