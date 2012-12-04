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

from webnotes.utils import flt, fmt_money, get_first_day, get_last_day, getdate
from webnotes.model import db_exists
from webnotes.model.wrapper import copy_doclist
from webnotes.model.code import get_obj
from webnotes import msgprint

sql = webnotes.conn.sql
	


class DocType:
	def __init__(self,d,dl):
		self.doc, self.doclist = d, dl

	# Validate mandatory
	#-------------------
	def check_mandatory(self):
		# Following fields are mandatory in GL Entry
		mandatory = ['account','remarks','voucher_type','voucher_no','fiscal_year','company']
		for k in mandatory:
			if not self.doc.fields.get(k):
				msgprint("%s is mandatory for GL Entry" % k)
				raise Exception
				
		# Zero value transaction is not allowed
		if not (flt(self.doc.debit) or flt(self.doc.credit)):
			msgprint("GL Entry: Debit or Credit amount is mandatory for %s" % self.doc.account)
			raise Exception
			
			
		# COMMMENTED below to allow zero amount (+ and -) entry in tax table
		# Debit and credit can not done at the same time
		#if flt(self.doc.credit) != 0 and flt(self.doc.debit) != 0:
		#	msgprint("Sorry you cannot credit and debit under same account head.")
		#	raise Exception, "Validation Error."
		
	# Cost center is required only if transaction made against pl account
	#--------------------------------------------------------------------
	def pl_must_have_cost_center(self):
		if sql("select name from tabAccount where name=%s and is_pl_account='Yes'", self.doc.account):
			if not self.doc.cost_center and self.doc.voucher_type != 'Period Closing Voucher':
				msgprint("Error: Cost Center must be specified for PL Account: %s" % self.doc.account)
				raise Exception
		else: # not pl
			if self.doc.cost_center:
				self.doc.cost_center = ''
		
	# Account must be ledger, active and not freezed
	#-----------------------------------------------
	def validate_account_details(self, adv_adj):
		ret = sql("select group_or_ledger, docstatus, freeze_account, company from tabAccount where name=%s", self.doc.account)
		
		# 1. Checks whether Account type is group or ledger
		if ret and ret[0][0]=='Group':
			msgprint("Error: All accounts must be Ledgers. Account %s is a group" % self.doc.account)
			raise Exception

		# 2. Checks whether Account is active
		if ret and ret[0][1]==2:
			msgprint("Error: All accounts must be Active. Account %s moved to Trash" % self.doc.account)
			raise Exception
			
		# 3. Account has been freezed for other users except account manager
		if ret and ret[0][2]== 'Yes' and not adv_adj and not 'Accounts Manager' in webnotes.user.get_roles():
			msgprint("Error: Account %s has been freezed. Only Accounts Manager can do transaction against this account." % self.doc.account)
			raise Exception
			
		# 4. Check whether account is within the company
		if ret and ret[0][3] != self.doc.company:
			msgprint("Account: %s does not belong to the company: %s" % (self.doc.account, self.doc.company))
			raise Exception
			
	# Posting date must be in selected fiscal year and fiscal year is active
	#-------------------------------------------------------------------------
	def validate_posting_date(self):
		fy = sql("select docstatus, year_start_date from `tabFiscal Year` where name=%s ", self.doc.fiscal_year)
		ysd = fy[0][1]
		yed = get_last_day(get_first_day(ysd,0,11))
		pd = getdate(self.doc.posting_date)
		if fy[0][0] == 2:
			msgprint("Fiscal Year is not active. You can restore it from Trash")
			raise Exception
		if pd < ysd or pd > yed:
			msgprint("Posting date must be in the Selected Financial Year")
			raise Exception
			
	
	# Nobody can do GL Entries where posting date is before freezing date except authorized person
	#----------------------------------------------------------------------------------------------
	def check_freezing_date(self, adv_adj):
		if not adv_adj:
			acc_frozen_upto = webnotes.conn.get_value('Global Defaults', None, 'acc_frozen_upto')
			if acc_frozen_upto:
				bde_auth_role = webnotes.conn.get_value( 'Global Defaults', None,'bde_auth_role')
				if getdate(self.doc.posting_date) <= getdate(acc_frozen_upto) and not bde_auth_role in webnotes.user.get_roles():
					msgprint("You are not authorized to do/modify back dated accounting entries before %s." % getdate(acc_frozen_upto).strftime('%d-%m-%Y'), raise_exception=1)

	def update_outstanding_amt(self):
		# get final outstanding amt
		bal = flt(sql("select sum(debit)-sum(credit) from `tabGL Entry` where against_voucher=%s and against_voucher_type=%s and ifnull(is_cancelled,'No') = 'No'", (self.doc.against_voucher, self.doc.against_voucher_type))[0][0] or 0.0)
		
		if self.doc.against_voucher_type=='Purchase Invoice':
			# amount to debit
			bal = -bal
			
		# Validation : Outstanding can not be negative
		if bal < 0 and self.doc.is_cancelled == 'No':
			msgprint("""Outstanding for Voucher %s will become %s. 
				Outstanding cannot be less than zero. Please match exact outstanding.""" % 
				 (self.doc.against_voucher, fmt_money(bal)))
			raise Exception
			
		# Update outstanding amt on against voucher
		sql("update `tab%s` set outstanding_amount=%s where name='%s'"%
		 	(self.doc.against_voucher_type, bal, self.doc.against_voucher))
		
					
	# Total outstanding can not be greater than credit limit for any time for any customer
	#---------------------------------------------------------------------------------------------
	def check_credit_limit(self):
		#check for user role Freezed
		master_type=sql("select master_type, master_name from `tabAccount` where name='%s' " %self.doc.account)
		tot_outstanding = 0	#needed when there is no GL Entry in the system for that acc head
		if (self.doc.voucher_type=='Journal Voucher' or self.doc.voucher_type=='Sales Invoice') and (master_type and master_type[0][0]=='Customer' and master_type[0][1]):
			dbcr = sql("select sum(debit),sum(credit) from `tabGL Entry` where account = '%s' and is_cancelled='No'" % self.doc.account)
			if dbcr:
				tot_outstanding = flt(dbcr[0][0])-flt(dbcr[0][1])+flt(self.doc.debit)-flt(self.doc.credit)
			get_obj('Account',self.doc.account).check_credit_limit(self.doc.account, self.doc.company, tot_outstanding)
	
	#for opening entry account can not be pl account
	#-----------------------------------------------
	def check_pl_account(self):
		if self.doc.is_opening=='Yes':
			is_pl_account=sql("select is_pl_account from `tabAccount` where name='%s'"%(self.doc.account))
			if is_pl_account and is_pl_account[0][0]=='Yes':
				msgprint("For opening balance entry account can not be a PL account")
				raise Exception

	# Validate
	# --------
	def validate(self):	# not called on cancel
		self.check_mandatory()
		self.pl_must_have_cost_center()
		self.validate_posting_date()
		self.doc.is_cancelled = 'No' # will be reset by GL Control if cancelled
		self.check_credit_limit()
		self.check_pl_account()

	# On Update
	#----------
	def on_update(self,adv_adj, cancel, update_outstanding = 'Yes'):
		# Account must be ledger, active and not freezed
		self.validate_account_details(adv_adj)
		
		# Posting date must be after freezing date
		self.check_freezing_date(adv_adj)

		# Update outstanding amt on against voucher
		if self.doc.against_voucher and self.doc.against_voucher_type not in ('Journal Voucher','POS') and update_outstanding == 'Yes':
			self.update_outstanding_amt()
