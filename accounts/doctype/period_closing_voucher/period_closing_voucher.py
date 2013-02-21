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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.	If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cstr, flt, getdate
from webnotes.model import db_exists
from webnotes.model.doc import Document
from webnotes.model.bean import copy_doclist
from webnotes.model.code import get_obj
from webnotes import msgprint

sql = webnotes.conn.sql
	


class DocType:
	def __init__(self,d,dl):
		self.doc, self.doclist = d, dl
		self.td, self.tc = 0, 0
		self.year_start_date = ''
		self.year_end_date = ''


	def validate_account_head(self):
		acc_det = sql("select debit_or_credit, is_pl_account, group_or_ledger, company \
			from `tabAccount` where name = '%s'" % (self.doc.closing_account_head))

		# Account should be under liability 
		if cstr(acc_det[0][0]) != 'Credit' or cstr(acc_det[0][1]) != 'No':
			msgprint("Account: %s must be created under 'Source of Funds'" % self.doc.closing_account_head)
			raise Exception
	 
		# Account must be a ledger
		if cstr(acc_det[0][2]) != 'Ledger':
			msgprint("Account %s must be a ledger" % self.doc.closing_account_head)
			raise Exception 
		
		# Account should belong to company selected 
		if cstr(acc_det[0][3]) != self.doc.company:
			msgprint("Account %s does not belong to Company %s ." % (self.doc.closing_account_head, self.doc.company))
			raise Exception 


	def validate_posting_date(self):
		yr = sql("""select year_start_date, adddate(year_start_date, interval 1 year)
			from `tabFiscal Year` where name=%s""", (self.doc.fiscal_year, ))
		self.year_start_date = yr and yr[0][0] or ''
		self.year_end_date = yr and yr[0][1] or ''
		
		# Posting Date should be within closing year
		if getdate(self.doc.posting_date) < getdate(self.year_start_date) or getdate(self.doc.posting_date) > getdate(self.year_end_date):
			msgprint("Posting Date should be within Closing Fiscal Year")
			raise Exception

		# Period Closing Entry
		pce = sql("select name from `tabPeriod Closing Voucher` \
			where posting_date > '%s' and fiscal_year = '%s' and docstatus = 1" \
			% (self.doc.posting_date, self.doc.fiscal_year))
		if pce and pce[0][0]:
			msgprint("Another Period Closing Entry: %s has been made after posting date: %s"\
			 % (cstr(pce[0][0]), self.doc.posting_date))
			raise Exception
		 
		
	def validate_pl_balances(self):
		income_bal = sql("select sum(ifnull(t1.debit,0))-sum(ifnull(t1.credit,0)) \
			from `tabGL Entry` t1, tabAccount t2 where t1.account = t2.name \
			and t1.posting_date between '%s' and '%s' and t2.debit_or_credit = 'Credit' \
			and t2.group_or_ledger = 'Ledger' and t2.is_pl_account = 'Yes' and t2.docstatus < 2 \
			and t2.company = '%s'" % (self.year_start_date, self.doc.posting_date, self.doc.company))
			
		expense_bal = sql("select sum(ifnull(t1.debit,0))-sum(ifnull(t1.credit,0)) \
			from `tabGL Entry` t1, tabAccount t2 where t1.account = t2.name \
			and t1.posting_date between '%s' and '%s' and t2.debit_or_credit = 'Debit' \
			and t2.group_or_ledger = 'Ledger' and t2.is_pl_account = 'Yes' and t2.docstatus < 2 \
			and t2.company = '%s'" % (self.year_start_date, self.doc.posting_date, self.doc.company))
		
		income_bal = income_bal and income_bal[0][0] or 0
		expense_bal = expense_bal and expense_bal[0][0] or 0
		
		if not income_bal and not expense_bal:
			msgprint("Both Income and Expense balances are zero. No Need to make Period Closing Entry.")
			raise Exception
		
		
	def get_pl_balances(self, d_or_c):
		"""Get account (pl) specific balance"""
		acc_bal = sql("select	t1.account, sum(ifnull(t1.debit,0))-sum(ifnull(t1.credit,0)) \
			from `tabGL Entry` t1, `tabAccount` t2 where t1.account = t2.name and t2.group_or_ledger = 'Ledger' \
 			and ifnull(t2.is_pl_account, 'No') = 'Yes' and ifnull(is_cancelled, 'No') = 'No' \
			and t2.debit_or_credit = '%s' and t2.docstatus < 2 and t2.company = '%s' \
			and t1.posting_date between '%s' and '%s' group by t1.account " \
			% (d_or_c, self.doc.company, self.year_start_date, self.doc.posting_date))
		return acc_bal

	 
	def make_gl_entries(self, acc_det):
		for a in acc_det:
			if flt(a[1]):
				fdict = {
					'account': a[0], 
					'cost_center': '', 
					'against': '', 
					'debit': flt(a[1]) < 0 and -1*flt(a[1]) or 0,
					'credit': flt(a[1]) > 0 and flt(a[1]) or 0,
					'remarks': self.doc.remarks, 
					'voucher_type': self.doc.doctype, 
					'voucher_no': self.doc.name, 
					'transaction_date': self.doc.transaction_date, 
					'posting_date': self.doc.posting_date, 
					'fiscal_year': self.doc.fiscal_year, 
					'against_voucher': '', 
					'against_voucher_type': '', 
					'company': self.doc.company, 
					'is_opening': 'No', 
					'aging_date': self.doc.posting_date
				}
			
				self.save_entry(fdict)
	 

	def save_entry(self, fdict, is_cancel = 'No'):
		# Create new GL entry object and map values
		le = Document('GL Entry')
		for k in fdict:
			le.fields[k] = fdict[k]
		
		le_obj = get_obj(doc=le)
		# validate except on_cancel
		if is_cancel == 'No':
			le_obj.validate()
			
			# update total debit / credit except on_cancel
			self.td += flt(le.credit)
			self.tc += flt(le.debit)

		# save
		le.save(1)
		le_obj.on_update(adv_adj = '', cancel = '')
 
		 	
	def validate(self):
		# validate account head
		self.validate_account_head()

		# validate posting date
		self.validate_posting_date()

		# check if pl balance:
		self.validate_pl_balances()


	def on_submit(self):
		
		# Makes closing entries for Expense Account
		in_acc_det = self.get_pl_balances('Credit')
		self.make_gl_entries(in_acc_det)

		# Makes closing entries for Expense Account
		ex_acc_det = self.get_pl_balances('Debit')
		self.make_gl_entries(ex_acc_det)


		# Makes Closing entry for Closing Account Head
		bal = self.tc - self.td
		self.make_gl_entries([[self.doc.closing_account_head, flt(bal)]])


	def on_cancel(self):
		# get all submit entries of current closing entry voucher
		gl_entries = sql("select account, debit, credit from `tabGL Entry` where voucher_type = 'Period Closing Voucher' and voucher_no = '%s' and ifnull(is_cancelled, 'No') = 'No'" % (self.doc.name))

		# Swap Debit & Credit Column and make gl entry
		for gl in gl_entries:
			fdict = {'account': gl[0], 'cost_center': '', 'against': '', 'debit': flt(gl[2]), 'credit' : flt(gl[1]), 'remarks': self.doc.cancel_reason, 'voucher_type': self.doc.doctype, 'voucher_no': self.doc.name, 'transaction_date': self.doc.transaction_date, 'posting_date': self.doc.posting_date, 'fiscal_year': self.doc.fiscal_year, 'against_voucher': '', 'against_voucher_type': '', 'company': self.doc.company, 'is_opening': 'No', 'aging_date': 'self.doc.posting_date'}
			self.save_entry(fdict, is_cancel = 'Yes')

		# Update is_cancelled = 'Yes' to all gl entries for current voucher
		sql("update `tabGL Entry` set is_cancelled = 'Yes' where voucher_type = '%s' and voucher_no = '%s'" % (self.doc.doctype, self.doc.name))