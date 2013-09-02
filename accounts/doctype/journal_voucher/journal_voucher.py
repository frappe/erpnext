# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cint, cstr, flt, fmt_money, formatdate, getdate
from webnotes.model.doc import addchild
from webnotes.model.bean import getlist
from webnotes import msgprint
from setup.utils import get_company_currency

from controllers.accounts_controller import AccountsController

class DocType(AccountsController):
	def __init__(self,d,dl):
		self.doc, self.doclist = d,dl
		self.master_type = {}
		self.credit_days_for = {}
		self.credit_days_global = -1
		self.is_approving_authority = -1

	def validate(self):
		if not self.doc.is_opening:
			self.doc.is_opening='No'
			
		self.doc.clearance_date = None
		
		super(DocType, self).validate_date_with_fiscal_year()
		
		self.validate_debit_credit()
		self.validate_cheque_info()
		self.validate_entries_for_advance()
		self.validate_against_jv()
		
		self.set_against_account()
		self.create_remarks()
		self.set_aging_date()
		self.set_print_format_fields()

	
	def on_submit(self):
		if self.doc.voucher_type in ['Bank Voucher', 'Contra Voucher', 'Journal Entry']:
			self.check_credit_days()
		self.check_account_against_entries()
		self.make_gl_entries()

	def on_cancel(self):
		from accounts.utils import remove_against_link_from_jv
		remove_against_link_from_jv(self.doc.doctype, self.doc.name, "against_jv")
		
		self.make_gl_entries(cancel=1)
		
	def on_trash(self):
		pass
		#if self.doc.amended_from:
		#	webnotes.delete_doc("Journal Voucher", self.doc.amended_from)

	def validate_debit_credit(self):
		for d in getlist(self.doclist, 'entries'):
			if d.debit and d.credit:
				msgprint("You cannot credit and debit same account at the same time.", 
				 	raise_exception=1)

	def validate_cheque_info(self):
		if self.doc.voucher_type in ['Bank Voucher']:
			if not self.doc.cheque_no or not self.doc.cheque_date:
				msgprint("Reference No & Reference Date is required for %s" %
				self.doc.voucher_type, raise_exception=1)
				
		if self.doc.cheque_date and not self.doc.cheque_no:
			msgprint("Reference No is mandatory if you entered Reference Date", raise_exception=1)

	def validate_entries_for_advance(self):
		for d in getlist(self.doclist,'entries'):
			if not d.is_advance and not d.against_voucher and \
					not d.against_invoice and not d.against_jv:
				master_type = webnotes.conn.get_value("Account", d.account, "master_type")
				if (master_type == 'Customer' and flt(d.credit) > 0) or \
						(master_type == 'Supplier' and flt(d.debit) > 0):
					msgprint("Message: Please check Is Advance as 'Yes' against \
						Account %s if this is an advance entry." % d.account)

	def validate_against_jv(self):
		for d in getlist(self.doclist, 'entries'):
			if d.against_jv:
				if d.against_jv == self.doc.name:
					msgprint("You can not enter current voucher in 'Against JV' column",
						raise_exception=1)
				elif not webnotes.conn.sql("""select name from `tabJournal Voucher Detail` 
						where account = '%s' and docstatus = 1 and parent = '%s'""" % 
						(d.account, d.against_jv)):
					msgprint("Against JV: %s is not valid." % d.against_jv, raise_exception=1)
		
	def set_against_account(self):
		# Debit = Credit
		debit, credit = 0.0, 0.0
		debit_list, credit_list = [], []
		for d in getlist(self.doclist, 'entries'):
			debit += flt(d.debit, 2)
			credit += flt(d.credit, 2)
			if flt(d.debit)>0 and (d.account not in debit_list): debit_list.append(d.account)
			if flt(d.credit)>0 and (d.account not in credit_list): credit_list.append(d.account)

		self.doc.total_debit = debit
		self.doc.total_credit = credit

		if abs(self.doc.total_debit-self.doc.total_credit) > 0.001:
			msgprint("Debit must be equal to Credit. The difference is %s" % 
			 	(self.doc.total_debit-self.doc.total_credit), raise_exception=1)
		
		# update against account
		for d in getlist(self.doclist, 'entries'):
			if flt(d.debit) > 0: d.against_account = ', '.join(credit_list)
			if flt(d.credit) > 0: d.against_account = ', '.join(debit_list)

	def create_remarks(self):
		r = []
		if self.doc.cheque_no :
			if self.doc.cheque_date:
				r.append('Via Reference #%s dated %s' % 
					(self.doc.cheque_no, formatdate(self.doc.cheque_date)))
			else :
				msgprint("Please enter Reference date", raise_exception=1)
		
		for d in getlist(self.doclist, 'entries'):
			if d.against_invoice and d.credit:
				currency = webnotes.conn.get_value("Sales Invoice", d.against_invoice, "currency")
				r.append('%s %s against Invoice: %s' % 
					(cstr(currency), fmt_money(flt(d.credit)), d.against_invoice))
					
			if d.against_voucher and d.debit:
				bill_no = webnotes.conn.sql("""select bill_no, bill_date, currency 
					from `tabPurchase Invoice` where name=%s""", d.against_voucher)
				if bill_no and bill_no[0][0] and bill_no[0][0].lower().strip() \
						not in ['na', 'not applicable', 'none']:
					r.append('%s %s against Bill %s dated %s' % 
						(cstr(bill_no[0][2]), fmt_money(flt(d.debit)), bill_no[0][0], 
						bill_no[0][1] and formatdate(bill_no[0][1].strftime('%Y-%m-%d')) or ''))
	
		if self.doc.user_remark:
			r.append("User Remark : %s"%self.doc.user_remark)

		if r:
			self.doc.remark = ("\n").join(r)
		else:
			webnotes.msgprint("User Remarks is mandatory", raise_exception=1)

	def set_aging_date(self):
		if self.doc.is_opening != 'Yes':
			self.doc.aging_date = self.doc.posting_date
		else:
			# check account type whether supplier or customer
			exists = False
			for d in getlist(self.doclist, 'entries'):
				account_type = webnotes.conn.get_value("Account", d.account, "account_type")
				if account_type in ["Supplier", "Customer"]:
					exists = True
					break

			# If customer/supplier account, aging date is mandatory
			if exists and not self.doc.aging_date: 
				msgprint("Aging Date is mandatory for opening entry", raise_exception=1)
			else:
				self.doc.aging_date = self.doc.posting_date

	def set_print_format_fields(self):
		for d in getlist(self.doclist, 'entries'):
			account_type, master_type = webnotes.conn.get_value("Account", d.account, 
				["account_type", "master_type"])
				
			if master_type in ['Supplier', 'Customer']:
				if not self.doc.pay_to_recd_from:
					self.doc.pay_to_recd_from = webnotes.conn.get_value(master_type, 
						' - '.join(d.account.split(' - ')[:-1]), 
						master_type == 'Customer' and 'customer_name' or 'supplier_name')
			
			if account_type == 'Bank or Cash':
				company_currency = get_company_currency(self.doc.company)
				amt = flt(d.debit) and d.debit or d.credit	
				self.doc.total_amount = company_currency +' '+ cstr(amt)
				from webnotes.utils import money_in_words
				self.doc.total_amount_in_words = money_in_words(amt, company_currency)

	def check_credit_days(self):
		date_diff = 0
		if self.doc.cheque_date:
			date_diff = (getdate(self.doc.cheque_date)-getdate(self.doc.posting_date)).days
		
		if date_diff <= 0: return
		
		# Get List of Customer Account
		acc_list = filter(lambda d: webnotes.conn.get_value("Account", d.account, 
		 	"master_type")=='Customer', getlist(self.doclist,'entries'))
		
		for d in acc_list:
			credit_days = self.get_credit_days_for(d.account)
			# Check credit days
			if credit_days > 0 and not self.get_authorized_user() and cint(date_diff) > credit_days:
				msgprint("Credit Not Allowed: Cannot allow a check that is dated \
					more than %s days after the posting date" % credit_days, raise_exception=1)
					
	def get_credit_days_for(self, ac):
		if not self.credit_days_for.has_key(ac):
			self.credit_days_for[ac] = cint(webnotes.conn.get_value("Account", ac, "credit_days"))

		if not self.credit_days_for[ac]:
			if self.credit_days_global==-1:
				self.credit_days_global = cint(webnotes.conn.get_value("Company", 
					self.doc.company, "credit_days"))
					
			return self.credit_days_global
		else:
			return self.credit_days_for[ac]

	def get_authorized_user(self):
		if self.is_approving_authority==-1:
			self.is_approving_authority = 0

			# Fetch credit controller role
			approving_authority = webnotes.conn.get_value("Global Defaults", None, 
				"credit_controller")
			
			# Check logged-in user is authorized
			if approving_authority in webnotes.user.get_roles():
				self.is_approving_authority = 1
				
		return self.is_approving_authority

	def check_account_against_entries(self):
		for d in self.doclist.get({"parentfield": "entries"}):
			if d.against_invoice and webnotes.conn.get_value("Sales Invoice", 
					d.against_invoice, "debit_to") != d.account:
				webnotes.throw(_("Credited account (Customer) is not matching with Sales Invoice"))
			
			if d.against_voucher and webnotes.conn.get_value("Purchase Invoice", 
						d.against_voucher, "credit_to") != d.account:
				webnotes.throw(_("Debited account (Supplier) is not matching with \
					Purchase Invoice"))

	def make_gl_entries(self, cancel=0, adv_adj=0):
		from accounts.general_ledger import make_gl_entries
		gl_map = []
		for d in self.doclist.get({"parentfield": "entries"}):
			if d.debit or d.credit:
				gl_map.append(
					self.get_gl_dict({
						"account": d.account,
						"against": d.against_account,
						"debit": d.debit,
						"credit": d.credit,
						"against_voucher_type": ((d.against_voucher and "Purchase Invoice") 
							or (d.against_invoice and "Sales Invoice") 
							or (d.against_jv and "Journal Voucher")),
						"against_voucher": d.against_voucher or d.against_invoice or d.against_jv,
						"remarks": self.doc.remark,
						"cost_center": d.cost_center
					}, cancel)
				)
		if gl_map:
			make_gl_entries(gl_map, cancel=cancel, adv_adj=adv_adj)

	def get_outstanding(self, args):
		args = eval(args)
		o_s = webnotes.conn.sql("""select outstanding_amount from `tab%s` where name = %s""" % 
			(args['doctype'], '%s'), args['docname'])
		if args['doctype'] == 'Purchase Invoice':
			return {'debit': o_s and flt(o_s[0][0]) or 0}
		if args['doctype'] == 'Sales Invoice':
			return {'credit': o_s and flt(o_s[0][0]) or 0}
	
	def get_balance(self):
		if not getlist(self.doclist,'entries'):
			msgprint("Please enter atleast 1 entry in 'GL Entries' table")
		else:
			flag, self.doc.total_debit, self.doc.total_credit = 0, 0, 0
			diff = flt(self.doc.difference, 2)
			
			# If any row without amount, set the diff on that row
			for d in getlist(self.doclist,'entries'):
				if not d.credit and not d.debit and diff != 0:
					if diff>0:
						d.credit = diff
					elif diff<0:
						d.debit = diff
					flag = 1
					
			# Set the diff in a new row
			if flag == 0 and diff != 0:
				jd = addchild(self.doc, 'entries', 'Journal Voucher Detail', self.doclist)
				if diff>0:
					jd.credit = abs(diff)
				elif diff<0:
					jd.debit = abs(diff)
					
			# Set the total debit, total credit and difference
			for d in getlist(self.doclist,'entries'):
				self.doc.total_debit += flt(d.debit, 2)
				self.doc.total_credit += flt(d.credit, 2)

			self.doc.difference = flt(self.doc.total_debit, 2) - flt(self.doc.total_credit, 2)

	def get_outstanding_invoices(self):
		self.doclist = self.doc.clear_table(self.doclist, 'entries')
		total = 0
		for d in self.get_values():
			total += flt(d[2])
			jd = addchild(self.doc, 'entries', 'Journal Voucher Detail', self.doclist)
			jd.account = cstr(d[1])
			if self.doc.write_off_based_on == 'Accounts Receivable':
				jd.credit = flt(d[2])
				jd.against_invoice = cstr(d[0])
			elif self.doc.write_off_based_on == 'Accounts Payable':
				jd.debit = flt(d[2])
				jd.against_voucher = cstr(d[0])
			jd.save(1)
		jd = addchild(self.doc, 'entries', 'Journal Voucher Detail', self.doclist)
		if self.doc.write_off_based_on == 'Accounts Receivable':
			jd.debit = total
		elif self.doc.write_off_based_on == 'Accounts Payable':
			jd.credit = total
		jd.save(1)

	def get_values(self):
		cond = (flt(self.doc.write_off_amount) > 0) and \
			' and outstanding_amount <= '+ self.doc.write_off_amount or ''
		if self.doc.write_off_based_on == 'Accounts Receivable':
			return webnotes.conn.sql("""select name, debit_to, outstanding_amount 
				from `tabSales Invoice` where docstatus = 1 and company = %s 
				and outstanding_amount > 0 %s""" % ('%s', cond), self.doc.company)
		elif self.doc.write_off_based_on == 'Accounts Payable':
			return webnotes.conn.sql("""select name, credit_to, outstanding_amount 
				from `tabPurchase Invoice` where docstatus = 1 and company = %s 
				and outstanding_amount > 0 %s""" % ('%s', cond), self.doc.company)

@webnotes.whitelist()
def get_default_bank_cash_account(company, voucher_type):
	from accounts.utils import get_balance_on
	account = webnotes.conn.get_value("Company", company,
		voucher_type=="Bank Voucher" and "default_bank_account" or "default_cash_account")
	if account:
		return {
			"account": account,
			"balance": get_balance_on(account)
		}
		
@webnotes.whitelist()
def get_payment_entry_from_sales_invoice(sales_invoice):
	from accounts.utils import get_balance_on
	si = webnotes.bean("Sales Invoice", sales_invoice)
	jv = get_payment_entry(si.doc)
	jv.doc.remark = 'Payment received against Sales Invoice %(name)s. %(remarks)s' % si.doc.fields

	# credit customer
	jv.doclist[1].account = si.doc.debit_to
	jv.doclist[1].balance = get_balance_on(si.doc.debit_to)
	jv.doclist[1].credit = si.doc.outstanding_amount
	jv.doclist[1].against_invoice = si.doc.name

	# debit bank
	jv.doclist[2].debit = si.doc.outstanding_amount
	
	return [d.fields for d in jv.doclist]

@webnotes.whitelist()
def get_payment_entry_from_purchase_invoice(purchase_invoice):
	from accounts.utils import get_balance_on
	pi = webnotes.bean("Purchase Invoice", purchase_invoice)
	jv = get_payment_entry(pi.doc)
	jv.doc.remark = 'Payment against Purchase Invoice %(name)s. %(remarks)s' % pi.doc.fields
	
	# credit supplier
	jv.doclist[1].account = pi.doc.credit_to
	jv.doclist[1].balance = get_balance_on(pi.doc.credit_to)
	jv.doclist[1].debit = pi.doc.outstanding_amount
	jv.doclist[1].against_voucher = pi.doc.name

	# credit bank
	jv.doclist[2].credit = pi.doc.outstanding_amount
	
	return [d.fields for d in jv.doclist]

def get_payment_entry(doc):
	bank_account = get_default_bank_cash_account(doc.company, "Bank Voucher")
	
	jv = webnotes.new_bean('Journal Voucher')
	jv.doc.voucher_type = 'Bank Voucher'

	jv.doc.company = doc.company
	jv.doc.fiscal_year = doc.fiscal_year

	jv.doclist.append({
		"doctype": "Journal Voucher Detail",
		"parentfield": "entries"
	})

	jv.doclist.append({
		"doctype": "Journal Voucher Detail",
		"parentfield": "entries"
	})
	
	if bank_account:
		jv.doclist[2].account = bank_account["account"]
		jv.doclist[2].balance = bank_account["balance"]
	
	return jv
	
@webnotes.whitelist()
def get_opening_accounts(company):
	"""get all balance sheet accounts for opening entry"""
	from accounts.utils import get_balance_on
	accounts = webnotes.conn.sql_list("""select name from tabAccount 
		where group_or_ledger='Ledger' and is_pl_account='No' and company=%s""", company)
	
	return [{"account": a, "balance": get_balance_on(a)} for a in accounts]
	
def get_against_purchase_invoice(doctype, txt, searchfield, start, page_len, filters):
	return webnotes.conn.sql("""select name, credit_to, outstanding_amount, bill_no, bill_date 
		from `tabPurchase Invoice` where credit_to = %s and docstatus = 1 
		and outstanding_amount > 0 and %s like %s order by name desc limit %s, %s""" %
		("%s", searchfield, "%s", "%s", "%s"), 
		(filters["account"], "%%%s%%" % txt, start, page_len))
		
def get_against_sales_invoice(doctype, txt, searchfield, start, page_len, filters):
	return webnotes.conn.sql("""select name, debit_to, outstanding_amount 
		from `tabSales Invoice` where debit_to = %s and docstatus = 1 
		and outstanding_amount > 0 and `%s` like %s order by name desc limit %s, %s""" %
		("%s", searchfield, "%s", "%s", "%s"), 
		(filters["account"], "%%%s%%" % txt, start, page_len))
		
def get_against_jv(doctype, txt, searchfield, start, page_len, filters):
	return webnotes.conn.sql("""select jv.name, jv.posting_date, jv.user_remark 
		from `tabJournal Voucher` jv, `tabJournal Voucher Detail` jv_detail 
		where jv_detail.parent = jv.name and jv_detail.account = %s and jv.docstatus = 1 
		and jv.%s like %s order by jv.name desc limit %s, %s""" % 
		("%s", searchfield, "%s", "%s", "%s"), 
		(filters["account"], "%%%s%%" % txt, start, page_len))