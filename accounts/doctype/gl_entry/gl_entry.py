# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import flt, fmt_money, getdate
from webnotes.model.code import get_obj
from webnotes import msgprint, _
	
class DocType:
	def __init__(self,d,dl):
		self.doc, self.doclist = d, dl

	def validate(self):
		self.check_mandatory()
		self.pl_must_have_cost_center()
		self.validate_posting_date()
		self.check_pl_account()
		self.validate_cost_center()

	def on_update_with_args(self, adv_adj, update_outstanding = 'Yes'):
		self.validate_account_details(adv_adj)
		validate_frozen_account(self.doc.account, adv_adj)
		check_freezing_date(self.doc.posting_date, adv_adj)
		check_negative_balance(self.doc.account, adv_adj)

		# Update outstanding amt on against voucher
		if self.doc.against_voucher and self.doc.against_voucher_type != "POS" \
			and update_outstanding == 'Yes':
				update_outstanding_amt(self.doc.account, self.doc.against_voucher_type, 
					self.doc.against_voucher)

	def check_mandatory(self):
		mandatory = ['account','remarks','voucher_type','voucher_no','fiscal_year','company']
		for k in mandatory:
			if not self.doc.fields.get(k):
				webnotes.throw(k + _(" is mandatory for GL Entry"))

		# Zero value transaction is not allowed
		if not (flt(self.doc.debit) or flt(self.doc.credit)):
			webnotes.throw(_("GL Entry: Debit or Credit amount is mandatory for ") + 
				self.doc.account)
			
	def pl_must_have_cost_center(self):
		if webnotes.conn.get_value("Account", self.doc.account, "is_pl_account") == "Yes":
			if not self.doc.cost_center and self.doc.voucher_type != 'Period Closing Voucher':
				webnotes.throw(_("Cost Center must be specified for PL Account: ") + 
					self.doc.account)
		elif self.doc.cost_center:
			self.doc.cost_center = None
		
	def validate_posting_date(self):
		from accounts.utils import validate_fiscal_year
		validate_fiscal_year(self.doc.posting_date, self.doc.fiscal_year, "Posting Date")

	def check_pl_account(self):
		if self.doc.is_opening=='Yes' and \
				webnotes.conn.get_value("Account", self.doc.account, "is_pl_account") == "Yes":
			webnotes.throw(_("For opening balance entry account can not be a PL account"))			

	def validate_account_details(self, adv_adj):
		"""Account must be ledger, active and not freezed"""
		
		ret = webnotes.conn.sql("""select group_or_ledger, docstatus, company 
			from tabAccount where name=%s""", self.doc.account, as_dict=1)[0]
		
		if ret.group_or_ledger=='Group':
			webnotes.throw(_("Account") + ": " + self.doc.account + _(" is not a ledger"))

		if ret.docstatus==2:
			webnotes.throw(_("Account") + ": " + self.doc.account + _(" is not active"))
			
		if ret.company != self.doc.company:
			webnotes.throw(_("Account") + ": " + self.doc.account + 
				_(" does not belong to the company") + ": " + self.doc.company)
				
	def validate_cost_center(self):
		if not hasattr(self, "cost_center_company"):
			self.cost_center_company = {}
		
		def _get_cost_center_company():
			if not self.cost_center_company.get(self.doc.cost_center):
				self.cost_center_company[self.doc.cost_center] = webnotes.conn.get_value(
					"Cost Center", self.doc.cost_center, "company")
			
			return self.cost_center_company[self.doc.cost_center]
			
		if self.doc.cost_center and _get_cost_center_company() != self.doc.company:
				webnotes.throw(_("Cost Center") + ": " + self.doc.cost_center + 
					_(" does not belong to the company") + ": " + self.doc.company)
						
def check_negative_balance(account, adv_adj=False):
	if not adv_adj and account:
		account_details = webnotes.conn.get_value("Account", account, 
				["allow_negative_balance", "debit_or_credit"], as_dict=True)
		if not account_details["allow_negative_balance"]:
			balance = webnotes.conn.sql("""select sum(debit) - sum(credit) from `tabGL Entry` 
				where account = %s""", account)
			balance = account_details["debit_or_credit"] == "Debit" and \
				flt(balance[0][0]) or -1*flt(balance[0][0])
		
			if flt(balance) < 0:
				webnotes.throw(_("Negative balance is not allowed for account ") + account)

def check_freezing_date(posting_date, adv_adj=False):
	"""
		Nobody can do GL Entries where posting date is before freezing date 
		except authorized person
	"""
	if not adv_adj:
		acc_frozen_upto = webnotes.conn.get_value('Accounts Settings', None, 'acc_frozen_upto')
		if acc_frozen_upto:
			bde_auth_role = webnotes.conn.get_value( 'Accounts Settings', None,'bde_auth_role')
			if getdate(posting_date) <= getdate(acc_frozen_upto) \
					and not bde_auth_role in webnotes.user.get_roles():
				webnotes.throw(_("You are not authorized to do/modify back dated entries before ")
					+ getdate(acc_frozen_upto).strftime('%d-%m-%Y'))

def update_outstanding_amt(account, against_voucher_type, against_voucher, on_cancel=False):
	# get final outstanding amt
	bal = flt(webnotes.conn.sql("""select sum(ifnull(debit, 0)) - sum(ifnull(credit, 0)) 
		from `tabGL Entry` 
		where against_voucher_type=%s and against_voucher=%s and account = %s""", 
		(against_voucher_type, against_voucher, account))[0][0] or 0.0)

	if against_voucher_type == 'Purchase Invoice':
		bal = -bal
	elif against_voucher_type == "Journal Voucher":
		against_voucher_amount = flt(webnotes.conn.sql("""
			select sum(ifnull(debit, 0)) - sum(ifnull(credit, 0))
			from `tabGL Entry` where voucher_type = 'Journal Voucher' and voucher_no = %s
			and account = %s""", (against_voucher, account))[0][0])
		bal = against_voucher_amount + bal
		if against_voucher_amount < 0:
			bal = -bal
		
	# Validation : Outstanding can not be negative
	if bal < 0 and not on_cancel:
		webnotes.throw(_("Outstanding for Voucher ") + against_voucher + _(" will become ") + 
			fmt_money(bal) + _(". Outstanding cannot be less than zero. \
			 	Please match exact outstanding."))
		
	# Update outstanding amt on against voucher
	if against_voucher_type in ["Sales Invoice", "Purchase Invoice"]:
		webnotes.conn.sql("update `tab%s` set outstanding_amount=%s where name='%s'" %
		 	(against_voucher_type, bal, against_voucher))
			
def validate_frozen_account(account, adv_adj):
	frozen_account = webnotes.conn.get_value("Account", account, "freeze_account")
	if frozen_account == 'Yes' and not adv_adj:
		frozen_accounts_modifier = webnotes.conn.get_value( 'Accounts Settings', None, 
			'frozen_accounts_modifier')
		if not frozen_accounts_modifier:
			webnotes.throw(account + _(" is a frozen account. \
				Either make the account active or assign role in Accounts Settings \
				who can create / modify entries against this account"))
		elif frozen_accounts_modifier not in webnotes.user.get_roles():
			webnotes.throw(account + _(" is a frozen account. ") + 
				_("To create / edit transactions against this account, you need role") + ": " +  
				frozen_accounts_modifier)
