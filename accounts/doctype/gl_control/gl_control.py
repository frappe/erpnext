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

from webnotes.utils import cstr, flt, get_defaults
from webnotes.model.doc import addchild
from webnotes.model.wrapper import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint

class DocType:
	def __init__(self,d,dl):
		self.doc, self.doclist = d, dl
		self.entries = []

	def get_period_difference(self,arg, cost_center =''):
		# used in General Ledger Page Report
		# used for Budget where cost center passed as extra argument
		acc, f, t = arg.split('~~~')
		c, fy = '', get_defaults()['fiscal_year']

		det = webnotes.conn.sql("select debit_or_credit, lft, rgt, is_pl_account from tabAccount where name=%s", acc)
		if f: c += (' and t1.posting_date >= "%s"' % f)
		if t: c += (' and t1.posting_date <= "%s"' % t)
		if cost_center: c += (' and t1.cost_center = "%s"' % cost_center)
		bal = webnotes.conn.sql("select sum(ifnull(t1.debit,0))-sum(ifnull(t1.credit,0)) from `tabGL Entry` t1 where t1.account='%s' %s" % (acc, c))
		bal = bal and flt(bal[0][0]) or 0

		if det[0][0] != 'Debit':
			bal = (-1) * bal

		return flt(bal)

	def add_ac(self,arg):
		ac = webnotes.model_wrapper(eval(arg))
		ac.doc.doctype = "Account"
		ac.doc.old_parent = ""
		ac.doc.freeze_account = "No"
		ac.insert()

		return ac.doc.name

	def add_cc(self,arg):
		cc = webnotes.model_wrapper(eval(arg))
		cc.doc.doctype = "Cost Center"
		cc.doc.old_parent = ""
		cc.insert()

		return cc.doc.name
	
	def get_advances(self, obj, account_head, table_name,table_field_name, dr_or_cr):
		jv_detail = webnotes.conn.sql("""select t1.name, t1.remark, t2.%s, t2.name 
			from `tabJournal Voucher` t1, `tabJournal Voucher Detail` t2 
			where t1.name = t2.parent 
			and (t2.against_voucher is null or t2.against_voucher = '')
			and (t2.against_invoice is null or t2.against_invoice = '') 
			and (t2.against_jv is null or t2.against_jv = '') 
			and t2.account = '%s' and t2.is_advance = 'Yes' and t1.docstatus = 1 
			order by t1.posting_date""" % (dr_or_cr,account_head))
		# clear advance table
		obj.doclist = obj.doc.clear_table(obj.doclist,table_field_name)
		# Create advance table
		for d in jv_detail:
			add = addchild(obj.doc, table_field_name, table_name, obj.doclist)
			add.journal_voucher = d[0]
			add.jv_detail_no = d[3]
			add.remarks = d[1]
			add.advance_amount = flt(d[2])
			add.allocate_amount = 0
			
		return obj.doclist

	def clear_advances(self, obj,table_name,table_field_name):
		for d in getlist(obj.doclist,table_field_name):
			if not flt(d.allocated_amount):
				webnotes.conn.sql("update `tab%s` set parent = '' where name = '%s' \
					and parent = '%s'" % (table_name, d.name, d.parent))
				d.parent = ''

	def reconcile_against_document(self, args):
		"""
			Cancel JV, Update aginst document, split if required and resubmit jv
		"""
		
		for d in args:
			self.check_if_jv_modified(d)

			against_fld = {
				'Journal Voucher' : 'against_jv',
				'Sales Invoice' : 'against_invoice',
				'Purchase Invoice' : 'against_voucher'
			}
			
			d['against_fld'] = against_fld[d['against_voucher_type']]

			# cancel JV
			jv_obj = get_obj('Journal Voucher', d['voucher_no'], with_children=1)
			self.make_gl_entries(jv_obj.doc, jv_obj.doclist, cancel =1, adv_adj =1)

			# update ref in JV Detail
			self.update_against_doc(d, jv_obj)

			# re-submit JV
			jv_obj = get_obj('Journal Voucher', d['voucher_no'], with_children =1)
			self.make_gl_entries(jv_obj.doc, jv_obj.doclist, cancel = 0, adv_adj =1)

	def update_against_doc(self, d, jv_obj):
		"""
			Updates against document, if partial amount splits into rows
		"""

		webnotes.conn.sql("""
			update `tabJournal Voucher Detail` t1, `tabJournal Voucher` t2	
			set t1.%(dr_or_cr)s = '%(allocated_amt)s', 
			t1.%(against_fld)s = '%(against_voucher)s', t2.modified = now() 
			where t1.name = '%(voucher_detail_no)s' and t1.parent = t2.name""" % d)
		
		if d['allocated_amt'] < d['unadjusted_amt']:
			jvd = webnotes.conn.sql("select cost_center, balance, against_account, is_advance from `tabJournal Voucher Detail` where name = '%s'" % d['voucher_detail_no'])
			# new entry with balance amount
			ch = addchild(jv_obj.doc, 'entries', 'Journal Voucher Detail')
			ch.account = d['account']
			ch.cost_center = cstr(jvd[0][0])
			ch.balance = cstr(jvd[0][1])
			ch.fields[d['dr_or_cr']] = flt(d['unadjusted_amt']) - flt(d['allocated_amt'])
			ch.fields[d['dr_or_cr']== 'debit' and 'credit' or 'debit'] = 0
			ch.against_account = cstr(jvd[0][2])
			ch.is_advance = cstr(jvd[0][3])
			ch.docstatus = 1
			ch.save(1)

	def check_if_jv_modified(self, args):
		"""
			check if there is already a voucher reference
			check if amount is same
			check if jv is submitted
		"""
		ret = webnotes.conn.sql("""
			select t2.%(dr_or_cr)s from `tabJournal Voucher` t1, `tabJournal Voucher Detail` t2 
			where t1.name = t2.parent and t2.account = '%(account)s' 
			and ifnull(t2.against_voucher, '')='' and ifnull(t2.against_invoice, '')='' and ifnull(t2.against_jv, '')=''
			and t1.name = '%(voucher_no)s' and t2.name = '%(voucher_detail_no)s'
			and t1.docstatus=1 and t2.%(dr_or_cr)s = %(unadjusted_amt)s
		""" % (args))
		
		if not ret:
			msgprint("Payment Entry has been modified after you pulled it. Please pull it again.", raise_exception=1)