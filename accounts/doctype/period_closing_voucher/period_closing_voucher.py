# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cstr, flt, getdate
from webnotes import msgprint, _
from controllers.accounts_controller import AccountsController

class DocType(AccountsController):
	def __init__(self,d,dl):
		self.doc, self.doclist = d, dl
		self.year_start_date = ''

	def validate(self):
		self.validate_account_head()
		self.validate_posting_date()
		self.validate_pl_balances()

	def on_submit(self):
		self.make_gl_entries()

	def on_cancel(self):
		webnotes.conn.sql("""delete from `tabGL Entry` 
			where voucher_type = 'Period Closing Voucher' and voucher_no=%s""", self.doc.name)

	def validate_account_head(self):
		debit_or_credit, is_pl_account = webnotes.conn.get_value("Account", 
			self.doc.closing_account_head, ["debit_or_credit", "is_pl_account"])
			
		if debit_or_credit != 'Credit' or is_pl_account != 'No':
			webnotes.throw(_("Account") + ": " + self.doc.closing_account_head + 
				_("must be a Liability account"))

	def validate_posting_date(self):
		from accounts.utils import get_fiscal_year
		self.year_start_date = get_fiscal_year(self.doc.posting_date)[1]

		pce = webnotes.conn.sql("""select name from `tabPeriod Closing Voucher`
			where posting_date > %s and fiscal_year = %s and docstatus = 1""", 
			(self.doc.posting_date, self.doc.fiscal_year))
		if pce and pce[0][0]:
			webnotes.throw(_("Another Period Closing Entry") + ": " + cstr(pce[0][0]) + 
				  _("has been made after posting date") + ": " + self.doc.posting_date)
		 
	def validate_pl_balances(self):
		income_bal = webnotes.conn.sql("""
			select sum(ifnull(t1.debit,0))-sum(ifnull(t1.credit,0)) 
			from `tabGL Entry` t1, tabAccount t2 
			where t1.account = t2.name and t1.posting_date between %s and %s 
			and t2.debit_or_credit = 'Credit' and t2.is_pl_account = 'Yes' 
			and t2.docstatus < 2 and t2.company = %s""", 
			(self.year_start_date, self.doc.posting_date, self.doc.company))
			
		expense_bal = webnotes.conn.sql("""
			select sum(ifnull(t1.debit,0))-sum(ifnull(t1.credit,0))
			from `tabGL Entry` t1, tabAccount t2 
			where t1.account = t2.name and t1.posting_date between %s and %s
			and t2.debit_or_credit = 'Debit' and t2.is_pl_account = 'Yes' 
			and t2.docstatus < 2 and t2.company=%s""", 
			(self.year_start_date, self.doc.posting_date, self.doc.company))
		
		income_bal = income_bal and income_bal[0][0] or 0
		expense_bal = expense_bal and expense_bal[0][0] or 0
		
		if not income_bal and not expense_bal:
			webnotes.throw(_("Both Income and Expense balances are zero. \
				No Need to make Period Closing Entry."))
		
	def get_pl_balances(self):
		"""Get balance for pl accounts"""
		return webnotes.conn.sql("""
			select t1.account, sum(ifnull(t1.debit,0))-sum(ifnull(t1.credit,0)) as balance
			from `tabGL Entry` t1, `tabAccount` t2 
			where t1.account = t2.name and ifnull(t2.is_pl_account, 'No') = 'Yes'
			and t2.docstatus < 2 and t2.company = %s 
			and t1.posting_date between %s and %s 
			group by t1.account
		""", (self.doc.company, self.year_start_date, self.doc.posting_date), as_dict=1)
	 
	def make_gl_entries(self):
		gl_entries = []
		net_pl_balance = 0
		pl_accounts = self.get_pl_balances()
		for acc in pl_accounts:
			if flt(acc.balance):
				gl_entries.append(self.get_gl_dict({
					"account": acc.account,
					"debit": abs(flt(acc.balance)) if flt(acc.balance) < 0 else 0,
					"credit": abs(flt(acc.balance)) if flt(acc.balance) > 0 else 0,
				}))
			
				net_pl_balance += flt(acc.balance)

		if net_pl_balance:
			gl_entries.append(self.get_gl_dict({
				"account": self.doc.closing_account_head,
				"debit": abs(net_pl_balance) if net_pl_balance > 0 else 0,
				"credit": abs(net_pl_balance) if net_pl_balance < 0 else 0
			}))
			
		from accounts.general_ledger import make_gl_entries
		make_gl_entries(gl_entries)
