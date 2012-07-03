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

# Please edit this list and import only required elements
import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, generate_hash, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, sendmail, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, getchildren, make_autoname
from webnotes.model.doclist import getlist, copy_doclist
from webnotes.model.code import get_obj, get_server_obj, run_server_obj, updatedb, check_syntax
from webnotes import session, form, is_testing, msgprint, errprint

set = webnotes.conn.set
sql = webnotes.conn.sql
get_value = webnotes.conn.get_value
in_transaction = webnotes.conn.in_transaction
convert_to_lists = webnotes.conn.convert_to_lists
	
# -----------------------------------------------------------------------------------------


class DocType:
	def __init__(self, doc, doclist):
		self.doc = doc
		self.doclist = doclist
		self.acc_type = self.doc.account and sql("select debit_or_credit from `tabAccount` where name = %s", self.doc.account)[0][0].lower() or ''
		self.dt = {
			'Sales Invoice': 'Sales Invoice',
			'Purchase Invoice': 'Purchase Invoice',
			'Journal Voucher': 'Journal Voucher'
		}
		
	#--------------------------------------------------
	def get_voucher_details(self):
		tot_amt = sql("""
			select sum(%s) from `tabGL Entry` where 
			voucher_type = %s and voucher_no = %s 
			and account = %s and ifnull(is_cancelled, 'No') = 'No'
		"""% (self.acc_type, '%s', '%s', '%s'), (self.dt[self.doc.voucher_type], self.doc.voucher_no, self.doc.account))
		
		outstanding = sql("""
			select sum(%s) - sum(%s) from `tabGL Entry` where 
			against_voucher = %s and voucher_no != %s
			and account = %s and ifnull(is_cancelled, 'No') = 'No'
		""" % ((self.acc_type == 'debit' and 'credit' or 'debit'), self.acc_type, '%s', '%s', '%s'), (self.doc.voucher_no, self.doc.voucher_no, self.doc.account))
		
		ret = {
			'total_amount': flt(tot_amt[0][0]) or 0,	
			'pending_amt_to_reconcile': flt(tot_amt[0][0]) - flt(outstanding[0][0]) or 0
		}
		
		return ret

		
	#--------------------------------------------------
	def get_payment_entries(self):
		"""
			Get payment entries for the account and period
			Payment entry will be decided based on account type (Dr/Cr)
		"""

		self.doclist = self.doc.clear_table(self.doclist, 'ir_payment_details')		
		gle = self.get_gl_entries()
		self.create_payment_table(gle)

	#--------------------------------------------------
	def get_gl_entries(self):
		self.validate_mandatory()
		dc = self.acc_type == 'debit' and 'credit' or 'debit'
		
		cond = self.doc.from_date and " and t1.posting_date >= '" + self.doc.from_date + "'" or ""
		cond += self.doc.to_date and " and t1.posting_date <= '" + self.doc.to_date + "'"or ""
		
		cond += self.doc.amt_greater_than and ' and t2.' + dc+' >= ' + self.doc.amt_greater_than or ''
		cond += self.doc.amt_less_than and ' and t2.' + dc+' <= ' + self.doc.amt_less_than or ''

		gle = sql("""
			select t1.name as voucher_no, t1.posting_date, t1.total_debit as total_amt,  sum(ifnull(t2.credit, 0)) - sum(ifnull(t2.debit, 0)) as amt_due, t1.remark, t2.against_account, t2.name as voucher_detail_no
			from `tabJournal Voucher` t1, `tabJournal Voucher Detail` t2
			where t1.name = t2.parent  
			and t1.docstatus = 1 
			and t2.account = %s
			and ifnull(t2.against_voucher, '')='' and ifnull(t2.against_invoice, '')='' and ifnull(t2.against_jv, '')=''
			and t2.%s > 0
			%s
			group by t1.name, t2.name
		"""% ('%s', dc, cond), self.doc.account, as_dict=1)

		return gle

	#--------------------------------------------------
	def create_payment_table(self, gle):
		for d in gle:
			ch = addchild(self.doc, 'ir_payment_details', 'Payment to Invoice Matching Tool Detail', 1, self.doclist)
			ch.voucher_no = d.get('voucher_no')
			ch.posting_date = d.get('posting_date')
			ch.amt_due =  self.acc_type == 'debit' and flt(d.get('amt_due')) or -1*flt(d.get('amt_due'))
			ch.total_amt = flt(d.get('total_amt'))
			ch.against_account = d.get('against_account')
			ch.remarks = d.get('remark')
			ch.amt_to_be_reconciled = flt(ch.amt_due)
			ch.voucher_detail_no = d.get('voucher_detail_no')
			
	#--------------------------------------------------
	def validate_mandatory(self):
		if not self.doc.account:
			msgprint("Please select Account first", raise_exception=1)
	
	#--------------------------------------------------	
	def reconcile(self):
		"""
			Links booking and payment voucher
			1. cancel payment voucher
			2. split into multiple rows if partially adjusted, assign against voucher
			3. submit payment voucher
		"""
		if not self.doc.voucher_no or not sql("select name from `tab%s` where name = %s" %(self.dt[self.doc.voucher_type], '%s'),  self.doc.voucher_no):
			msgprint("Please select valid Voucher No to proceed", raise_exception=1)
		
		lst = []
		for d in getlist(self.doclist, 'ir_payment_details'):
			if d.selected and flt(d.amt_to_be_reconciled) > 0:
				args = {
					'voucher_no' : d.voucher_no,
					'voucher_detail_no' : d.voucher_detail_no, 
					'against_voucher_type' : self.dt[self.doc.voucher_type], 
					'against_voucher'  : self.doc.voucher_no,
					'account' : self.doc.account, 
					'is_advance' : 'No', 
					'dr_or_cr' :  self.acc_type=='debit' and 'credit' or 'debit', 
					'unadjusted_amt' : flt(d.amt_due),
					'allocated_amt' : flt(d.amt_to_be_reconciled)
				}
			
				lst.append(args)
		

		if lst:
			get_obj('GL Control').reconcile_against_document(lst)
			msgprint("Successfully reconciled.")
		else:
			msgprint("No payment entries selected.", raise_exception=1)
