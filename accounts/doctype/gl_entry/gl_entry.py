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

from webnotes.utils import flt, fmt_money, getdate
from webnotes.model.code import get_obj
from webnotes import msgprint, _

sql = webnotes.conn.sql
	
class DocType:
	def __init__(self,d,dl):
		self.doc, self.doclist = d, dl

	def validate(self):	# not called on cancel
		self.check_mandatory()
		self.pl_must_have_cost_center()
		self.validate_posting_date()
		self.doc.is_cancelled = 'No' # will be reset by GL Control if cancelled
		self.check_credit_limit()
		self.check_pl_account()

	def on_update(self, adv_adj, cancel, update_outstanding = 'Yes'):
		self.validate_account_details(adv_adj)
		self.validate_cost_center()
		self.check_freezing_date(adv_adj)
		self.check_negative_balance(adv_adj)

		# Update outstanding amt on against voucher
		if self.doc.against_voucher and self.doc.against_voucher_type != "POS" \
			and update_outstanding == 'Yes':
				self.update_outstanding_amt()

	def check_mandatory(self):
		mandatory = ['account','remarks','voucher_type','voucher_no','fiscal_year','company']
		for k in mandatory:
			if not self.doc.fields.get(k):
				msgprint(k + _(" is mandatory for GL Entry"), raise_exception=1)
				
		# Zero value transaction is not allowed
		if not (flt(self.doc.debit) or flt(self.doc.credit)):
			msgprint(_("GL Entry: Debit or Credit amount is mandatory for ") + self.doc.account, 
				raise_exception=1)
			
	def pl_must_have_cost_center(self):
		if webnotes.conn.get_value("Account", self.doc.account, "is_pl_account") == "Yes":
			if not self.doc.cost_center and self.doc.voucher_type != 'Period Closing Voucher':
				msgprint(_("Cost Center must be specified for PL Account: ") + self.doc.account, 
					raise_exception=1)
		else:
			if self.doc.cost_center:
				self.doc.cost_center = ""
		
	def validate_posting_date(self):
		from accounts.utils import validate_fiscal_year
		validate_fiscal_year(self.doc.posting_date, self.doc.fiscal_year, "Posting Date")

	def check_credit_limit(self):
		master_type, master_name = webnotes.conn.get_value("Account", 
			self.doc.account, ["master_type", "master_name"])
			
		tot_outstanding = 0	#needed when there is no GL Entry in the system for that acc head
		if (self.doc.voucher_type=='Journal Voucher' or self.doc.voucher_type=='Sales Invoice') \
				and (master_type =='Customer' and master_name):
			dbcr = sql("""select sum(debit), sum(credit) from `tabGL Entry` 
				where account = '%s' and is_cancelled='No'""" % self.doc.account)
			if dbcr:
				tot_outstanding = flt(dbcr[0][0]) - flt(dbcr[0][1]) + \
					flt(self.doc.debit) - flt(self.doc.credit)
			get_obj('Account',self.doc.account).check_credit_limit(self.doc.account, 
				self.doc.company, tot_outstanding)

	def check_pl_account(self):
		if self.doc.is_opening=='Yes' and \
				webnotes.conn.get_value("Account", self.doc.account, "is_pl_account") == "Yes":
			msgprint(_("For opening balance entry account can not be a PL account"), 
				raise_exception=1)			

	def validate_account_details(self, adv_adj):
		"""Account must be ledger, active and not freezed"""
		
		ret = sql("""select group_or_ledger, docstatus, freeze_account, company 
			from tabAccount where name=%s""", self.doc.account, as_dict=1)
		
		if ret and ret[0]["group_or_ledger"]=='Group':
			msgprint(_("Account") + ": " + self.doc.account + _(" is not a ledger"), raise_exception=1)

		if ret and ret[0]["docstatus"]==2:
			msgprint(_("Account") + ": " + self.doc.account + _(" is not active"), raise_exception=1)
			
		# Account has been freezed for other users except account manager
		if ret and ret[0]["freeze_account"]== 'Yes' and not adv_adj \
				and not 'Accounts Manager' in webnotes.user.get_roles():
			msgprint(_("Account") + ": " + self.doc.account + _(" has been freezed. \
				Only Accounts Manager can do transaction against this account"), raise_exception=1)
		
		if self.doc.is_cancelled in ("No", None) and ret and ret[0]["company"] != self.doc.company:
			msgprint(_("Account") + ": " + self.doc.account + _(" does not belong to the company") \
				+ ": " + self.doc.company, raise_exception=1)
				
	def validate_cost_center(self):
		if not hasattr(self, "cost_center_company"):
			self.cost_center_company = {}
		
		def _get_cost_center_company():
			if not self.cost_center_company.get(self.doc.cost_center):
				self.cost_center_company[self.doc.cost_center] = webnotes.conn.get_value("Cost Center",
					self.doc.cost_center, "company_name")
			
			return self.cost_center_company[self.doc.cost_center]
			
		if self.doc.is_cancelled in ("No", None) and \
			self.doc.cost_center and _get_cost_center_company() != self.doc.company:
				msgprint(_("Cost Center") + ": " + self.doc.cost_center \
					+ _(" does not belong to the company") + ": " + self.doc.company, raise_exception=True)
		
	def check_freezing_date(self, adv_adj):
		"""
			Nobody can do GL Entries where posting date is before freezing date 
			except authorized person
		"""
		if not adv_adj:
			acc_frozen_upto = webnotes.conn.get_value('Global Defaults', None, 'acc_frozen_upto')
			if acc_frozen_upto:
				bde_auth_role = webnotes.conn.get_value( 'Global Defaults', None,'bde_auth_role')
				if getdate(self.doc.posting_date) <= getdate(acc_frozen_upto) \
						and not bde_auth_role in webnotes.user.get_roles():
					msgprint(_("You are not authorized to do/modify back dated entries before ") + 
						getdate(acc_frozen_upto).strftime('%d-%m-%Y'), raise_exception=1)
						
	def check_negative_balance(self, adv_adj):
		if not adv_adj:
			account = webnotes.conn.get_value("Account", self.doc.account, 
					["allow_negative_balance", "debit_or_credit"], as_dict=True)
			if not account["allow_negative_balance"]:
				balance = webnotes.conn.sql("""select sum(debit) - sum(credit) from `tabGL Entry` 
					where account = %s and ifnull(is_cancelled, 'No') = 'No'""", self.doc.account)
				balance = account["debit_or_credit"] == "Debit" and \
					balance[0][0] or -1*balance[0][0]
			
				if flt(balance) < 0:
					msgprint(_("Negative balance is not allowed for account ") + self.doc.account, 
						raise_exception=1)

	def update_outstanding_amt(self):
		# get final outstanding amt
		bal = flt(sql("""select sum(debit) - sum(credit) from `tabGL Entry` 
			where against_voucher=%s and against_voucher_type=%s and account = %s
			and ifnull(is_cancelled,'No') = 'No'""", (self.doc.against_voucher, 
			self.doc.against_voucher_type, self.doc.account))[0][0] or 0.0)

		if self.doc.against_voucher_type == 'Purchase Invoice':
			bal = -bal
		
		elif self.doc.against_voucher_type == "Journal Voucher":
			against_voucher_amount = flt(webnotes.conn.sql("""select sum(debit) - sum(credit)
				from `tabGL Entry` where voucher_type = 'Journal Voucher' and voucher_no = %s
				and account = %s""", (self.doc.against_voucher, self.doc.account))[0][0])
			
			bal = against_voucher_amount + bal
			if against_voucher_amount < 0:
				bal = -bal
			
		# Validation : Outstanding can not be negative
		if bal < 0 and self.doc.is_cancelled == 'No':
			msgprint(_("Outstanding for Voucher ") + self.doc.against_voucher + 
				_(" will become ") + fmt_money(bal) + _(". Outstanding cannot be less than zero. \
				 	Please match exact outstanding."), raise_exception=1)
			
		# Update outstanding amt on against voucher
		if self.doc.against_voucher_type in ["Sales Invoice", "Purchase Invoice"]:
			sql("update `tab%s` set outstanding_amount=%s where name='%s'"%
			 	(self.doc.against_voucher_type, bal, self.doc.against_voucher))