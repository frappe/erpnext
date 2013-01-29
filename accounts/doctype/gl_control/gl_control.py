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
from webnotes.model.doc import Document, addchild
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
		ac.ignore_permission = 1
		ac.insert()

		return ac.doc.name

	# Add a new cost center
	#----------------------
	def add_cc(self,arg):
		cc = webnotes.model_wrapper(eval(arg))
		cc.doc.doctype = "Cost Center"
		cc.doc.old_parent = ""
		cc.ignore_permission = 1
		cc.insert()

		return cc.doc.name


	# Get field values from the voucher
	#------------------------------------------
	def get_val(self, src, d, parent=None):
		if not src:
			return None
		if src.startswith('parent:'):
			return parent.fields[src.split(':')[1]]
		elif src.startswith('value:'):
			return eval(src.split(':')[1])
		elif src:
			return d.fields.get(src)

	def check_if_in_list(self, le):
		for e in self.entries:
			if e.account == le.account and (cstr(e.against_voucher)==cstr(le.against_voucher)) and (cstr(e.against_voucher_type)==cstr(le.against_voucher_type)) and (cstr(e.cost_center)==cstr(le.cost_center)):
				return [e]
		return 0

	# Make a dictionary(le) for every gl entry and append to a list(self.entries)
	#----------------------------------------------------------------------------
	def make_single_entry(self,parent,d,le_map,cancel, merge_entries):
		if self.get_val(le_map['account'], d, parent) and \
				(self.get_val(le_map['debit'], d, parent) \
				or self.get_val(le_map['credit'], d, parent)):
			flist = ['account', 'cost_center', 'against', 'debit', 'credit', 'remarks',
			 	'voucher_type', 'voucher_no', 'posting_date', 'fiscal_year', 'against_voucher',
			 	'against_voucher_type', 'company', 'is_opening', 'aging_date']

			# Check budget before gl entry
			#check budget only if account is expense account
			is_expense_acct = webnotes.conn.sql("""select name from tabAccount 
				where is_pl_account='Yes' and debit_or_credit='Debit' 
				and name=%s""",self.get_val(le_map['account'], d, parent))
				
			if is_expense_acct and self.get_val(le_map['cost_center'], d, parent):
				get_obj('Budget Control').check_budget([self.get_val(le_map[k], d, parent) 
					for k in flist if k in ['account', 'cost_center', 'debit', 
					'credit', 'posting_date', 'fiscal_year', 'company']],cancel)

			# Create new GL entry object and map values
			le = Document('GL Entry')
			for k in flist:
				le.fields[k] = self.get_val(le_map[k], d, parent)
			# if there is already an entry in this account then just add it to that entry
			same_head = self.check_if_in_list(le)
			if same_head and merge_entries:
				same_head = same_head[0]
				same_head.debit	= flt(same_head.debit)	+ flt(le.debit)
				same_head.credit = flt(same_head.credit) + flt(le.credit)
			else:
				self.entries.append(le)
				

	def manage_debit_credit(self, cancel):
		total_debit, total_credit = 0, 0
		for le in self.entries:
			# round off upto 2 decimal
			le.debit = flt(le.debit, 2)
			le.credit = flt(le.credit, 2)

			#toggle debit, credit if negative entry
			if flt(le.debit) < 0 or flt(le.credit) < 0:
				tmp=le.debit
				le.debit, le.credit = abs(flt(le.credit)), abs(flt(tmp))
			
			# toggled debit/credit in two separate condition because both
			# should be executed at the time of cancellation when there is 
			# negative amount (tax discount)
			if cancel:
				tmp=le.debit
				le.debit, le.credit = abs(flt(le.credit)), abs(flt(tmp))
		
			# update total debit / credit
			total_debit += flt(le.debit, 2)
			total_credit += flt(le.credit, 2)
			
		diff = flt(total_debit - total_credit, 2)
		if abs(diff)==0.01:
			if self.entries[0].debit:
				self.entries[0].debit = self.entries[0].debit - diff
			elif self.entries[0].credit:
				self.entries[0].credit = self.entries[0].credit + diff
		elif abs(diff) > 0.01 and not cancel:
			# Due to old wrong entries(total debit!=total credit) some voucher should be cancelled
			msgprint("""Debit and Credit not equal for this voucher: Diff (Debit) is %s""" %
			 	diff, raise_exception=1)

	def save_entries(self, cancel, adv_adj, update_outstanding):
		self.manage_debit_credit(cancel)
		
		for le in self.entries:
			le_obj = get_obj(doc=le)
			# validate except on_cancel
			if not cancel:
				le_obj.validate()

			le.save(1)
			le_obj.on_update(adv_adj, cancel, update_outstanding)
			
			
	# Make Multiple Entries
	def make_gl_entries(self, doc, doclist, cancel=0, adv_adj = 0, use_mapper='', merge_entries = 1, update_outstanding='Yes'):
		self.entries = []
		# get entries
		le_map_list = webnotes.conn.sql("select * from `tabGL Mapper Detail` where parent = %s", use_mapper or doc.doctype, as_dict=1)
		for le_map in le_map_list:
			if le_map['table_field']:
				for d in getlist(doclist,le_map['table_field']):
					# purchase_tax_details is the table of other charges in purchase cycle
					if le_map['table_field'] != 'purchase_tax_details' or \
							(le_map['table_field'] == 'purchase_tax_details' and \
							d.fields.get('category') != 'Valuation'):
						self.make_single_entry(doc,d,le_map,cancel, merge_entries)
			else:
				self.make_single_entry(None,doc,le_map,cancel, merge_entries)

		# save entries
		self.save_entries(cancel, adv_adj, update_outstanding)

		# set as cancelled
		if cancel:
			vt = self.get_val(le_map['voucher_type'], doc, doc)
			vn = self.get_val(le_map['voucher_no'],	doc, doc)
			webnotes.conn.sql("update `tabGL Entry` set is_cancelled='Yes' where voucher_type=%s and voucher_no=%s", (vt, vn))
	
	# ADVANCE ALLOCATION
	#-------------------
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

	# Clear rows which is not adjusted
	#-------------------------------------
	def clear_advances(self, obj,table_name,table_field_name):
		for d in getlist(obj.doclist,table_field_name):
			if not flt(d.allocated_amount):
				webnotes.conn.sql("update `tab%s` set parent = '' where name = '%s' and parent = '%s'" % (table_name, d.name, d.parent))
				d.parent = ''

	# Update aginst document in journal voucher
	#------------------------------------------
	def update_against_document_in_jv(self, obj, table_field_name, against_document_no, against_document_doctype, account_head, dr_or_cr,doctype):
		for d in getlist(obj.doclist, table_field_name):
			self.validate_jv_entry(d, account_head, dr_or_cr)
			if flt(d.advance_amount) == flt(d.allocated_amount):
				# cancel JV
				jv_obj = get_obj('Journal Voucher', d.journal_voucher, with_children=1)
				get_obj(dt='GL Control').make_gl_entries(jv_obj.doc, jv_obj.doclist, cancel =1, adv_adj =1)

				# update ref in JV Detail
				webnotes.conn.sql("update `tabJournal Voucher Detail` set %s = '%s' where name = '%s'" % (doctype=='Purchase Invoice' and 'against_voucher' or 'against_invoice', cstr(against_document_no), d.jv_detail_no))

				# re-submit JV
				jv_obj = get_obj('Journal Voucher', d.journal_voucher, with_children =1)
				get_obj(dt='GL Control').make_gl_entries(jv_obj.doc, jv_obj.doclist, cancel = 0, adv_adj =1)

			elif flt(d.advance_amount) > flt(d.allocated_amount):
				# cancel JV
				jv_obj = get_obj('Journal Voucher', d.journal_voucher, with_children=1)
				get_obj(dt='GL Control').make_gl_entries(jv_obj.doc, jv_obj.doclist, cancel =1, adv_adj = 1)

				# add extra entries
				self.add_extra_entry(jv_obj, d.journal_voucher, d.jv_detail_no, flt(d.allocated_amount), account_head, doctype, dr_or_cr, against_document_no)

				# re-submit JV
				jv_obj = get_obj('Journal Voucher', d.journal_voucher, with_children =1)
				get_obj(dt='GL Control').make_gl_entries(jv_obj.doc, jv_obj.doclist, cancel = 0, adv_adj = 1)
			else:
				msgprint("Allocation amount cannot be greater than advance amount")
				raise Exception
				

	# Add extra row in jv detail for unadjusted amount
	#--------------------------------------------------
	def add_extra_entry(self,jv_obj,jv,jv_detail_no, allocate, account_head, doctype, dr_or_cr, against_document_no):
		# get old entry details

		jvd = webnotes.conn.sql("select %s, cost_center, balance, against_account from `tabJournal Voucher Detail` where name = '%s'" % (dr_or_cr,jv_detail_no))
		advance = jvd and flt(jvd[0][0]) or 0
		balance = flt(advance) - flt(allocate)

		# update old entry
		webnotes.conn.sql("update `tabJournal Voucher Detail` set %s = '%s', %s = '%s' where name = '%s'" % (dr_or_cr, flt(allocate), doctype == "Purchase Invoice" and 'against_voucher' or 'against_invoice',cstr(against_document_no), jv_detail_no))

		# new entry with balance amount
		add = addchild(jv_obj.doc, 'entries', 'Journal Voucher Detail', jv_obj.doclist)
		add.account = account_head
		add.cost_center = cstr(jvd[0][1])
		add.balance = cstr(jvd[0][2])
		add.fields[dr_or_cr] = balance
		add.against_account = cstr(jvd[0][3])
		add.is_advance = 'Yes'
		add.save(1)
		
	# check if advance entries are still valid
	# ----------------------------------------
	def validate_jv_entry(self, d, account_head, dr_or_cr):
		# 1. check if there is already a voucher reference
		# 2. check if amount is same
		# 3. check if is_advance is 'Yes'
		# 4. check if jv is submitted
		ret = webnotes.conn.sql("select t2.%s from `tabJournal Voucher` t1, `tabJournal Voucher Detail` t2 where t1.name = t2.parent and ifnull(t2.against_voucher, '') = '' and ifnull(t2.against_invoice, '') = '' and t2.account = '%s' and t1.name = '%s' and t2.name = '%s' and t2.is_advance = 'Yes' and t1.docstatus=1 and t2.%s = %s" % (dr_or_cr, account_head, d.journal_voucher, d.jv_detail_no, dr_or_cr, d.advance_amount))
		if (not ret):
			msgprint("Please click on 'Get Advances Paid' button as the advance entries have been changed.")
			raise Exception
		return


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
		

	def repost_illegal_cancelled(self, after_date='2011-01-01'):
		"""
			Find vouchers that are not cancelled correctly and repost them
		"""
		vl = webnotes.conn.sql("""
			select voucher_type, voucher_no, account, sum(debit) as sum_debit, sum(credit) as sum_credit
			from `tabGL Entry`
			where is_cancelled='Yes' and creation > %s
			group by voucher_type, voucher_no, account
			""", after_date, as_dict=1)

		ac_list = []
		for v in vl:
			if v['sum_debit'] != 0 or v['sum_credit'] != 0:
				ac_list.append(v['account'])

		fy_list = webnotes.conn.sql("""select name from `tabFiscal Year`
		where (%s between year_start_date and date_sub(date_add(year_start_date,interval 1 year), interval 1 day))
		or year_start_date > %s
		order by year_start_date ASC""", (after_date, after_date))

		for fy in fy_list:
			fy_obj = get_obj('Fiscal Year', fy[0])
			for a in set(ac_list):
				fy_obj.repost(a)
