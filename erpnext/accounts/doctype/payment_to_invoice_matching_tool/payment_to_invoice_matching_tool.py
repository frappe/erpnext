# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import flt
from webnotes.model.doc import addchild
from webnotes.model.bean import getlist
from webnotes import msgprint

class DocType:
	def __init__(self, doc, doclist):
		self.doc = doc
		self.doclist = doclist
	
	def set_account_type(self):
		self.doc.account_type = self.doc.account and \
			webnotes.conn.get_value("Account", self.doc.account, "debit_or_credit").lower() or ""
		
	def get_voucher_details(self):
		total_amount = webnotes.conn.sql("""select sum(%s) from `tabGL Entry` 
			where voucher_type = %s and voucher_no = %s 
			and account = %s""" % 
			(self.doc.account_type, '%s', '%s', '%s'), 
			(self.doc.voucher_type, self.doc.voucher_no, self.doc.account))
			
		total_amount = total_amount and flt(total_amount[0][0]) or 0
		reconciled_payment = webnotes.conn.sql("""
			select sum(ifnull(%s, 0)) - sum(ifnull(%s, 0)) from `tabGL Entry` where 
			against_voucher = %s and voucher_no != %s
			and account = %s""" % 
			((self.doc.account_type == 'debit' and 'credit' or 'debit'), self.doc.account_type, 
			 	'%s', '%s', '%s'), (self.doc.voucher_no, self.doc.voucher_no, self.doc.account))
			
		reconciled_payment = reconciled_payment and flt(reconciled_payment[0][0]) or 0
		ret = {
			'total_amount': total_amount,	
			'pending_amt_to_reconcile': total_amount - reconciled_payment
		}
		
		return ret

	def get_payment_entries(self):
		"""
			Get payment entries for the account and period
			Payment entry will be decided based on account type (Dr/Cr)
		"""

		self.doclist = self.doc.clear_table(self.doclist, 'ir_payment_details')		
		gle = self.get_gl_entries()
		self.create_payment_table(gle)

	def get_gl_entries(self):
		self.validate_mandatory()
		dc = self.doc.account_type == 'debit' and 'credit' or 'debit'
		
		cond = self.doc.from_date and " and t1.posting_date >= '" + self.doc.from_date + "'" or ""
		cond += self.doc.to_date and " and t1.posting_date <= '" + self.doc.to_date + "'"or ""
		
		cond += self.doc.amt_greater_than and \
			' and t2.' + dc+' >= ' + self.doc.amt_greater_than or ''
		cond += self.doc.amt_less_than and \
			' and t2.' + dc+' <= ' + self.doc.amt_less_than or ''

		gle = webnotes.conn.sql("""
			select t1.name as voucher_no, t1.posting_date, t1.total_debit as total_amt, 
			 	sum(ifnull(t2.credit, 0)) - sum(ifnull(t2.debit, 0)) as amt_due, t1.remark,
			 	t2.against_account, t2.name as voucher_detail_no
			from `tabJournal Voucher` t1, `tabJournal Voucher Detail` t2
			where t1.name = t2.parent and t1.docstatus = 1 and t2.account = %s
			and ifnull(t2.against_voucher, '')='' and ifnull(t2.against_invoice, '')='' 
			and ifnull(t2.against_jv, '')='' and t2.%s > 0 %s group by t1.name, t2.name """ % 
			('%s', dc, cond), self.doc.account, as_dict=1)

		return gle

	def create_payment_table(self, gle):
		for d in gle:
			ch = addchild(self.doc, 'ir_payment_details', 
				'Payment to Invoice Matching Tool Detail', self.doclist)
			ch.voucher_no = d.get('voucher_no')
			ch.posting_date = d.get('posting_date')
			ch.amt_due =  self.doc.account_type == 'debit' and flt(d.get('amt_due')) \
				or -1*flt(d.get('amt_due'))
			ch.total_amt = flt(d.get('total_amt'))
			ch.against_account = d.get('against_account')
			ch.remarks = d.get('remark')
			ch.voucher_detail_no = d.get('voucher_detail_no')
			
	def validate_mandatory(self):
		if not self.doc.account:
			msgprint("Please select Account first", raise_exception=1)
	
	def reconcile(self):
		"""
			Links booking and payment voucher
			1. cancel payment voucher
			2. split into multiple rows if partially adjusted, assign against voucher
			3. submit payment voucher
		"""
		if not self.doc.voucher_no or not webnotes.conn.sql("""select name from `tab%s` 
				where name = %s""" % (self.doc.voucher_type, '%s'), self.doc.voucher_no):
			msgprint("Please select valid Voucher No to proceed", raise_exception=1)
		
		lst = []
		for d in getlist(self.doclist, 'ir_payment_details'):
			if flt(d.amt_to_be_reconciled) > 0:
				args = {
					'voucher_no' : d.voucher_no,
					'voucher_detail_no' : d.voucher_detail_no, 
					'against_voucher_type' : self.doc.voucher_type, 
					'against_voucher'  : self.doc.voucher_no,
					'account' : self.doc.account, 
					'is_advance' : 'No', 
					'dr_or_cr' :  self.doc.account_type=='debit' and 'credit' or 'debit', 
					'unadjusted_amt' : flt(d.amt_due),
					'allocated_amt' : flt(d.amt_to_be_reconciled)
				}
			
				lst.append(args)
		
		if lst:
			from accounts.utils import reconcile_against_document
			reconcile_against_document(lst)
			msgprint("Successfully allocated.")
		else:
			msgprint("No amount allocated.", raise_exception=1)

def gl_entry_details(doctype, txt, searchfield, start, page_len, filters):
	from controllers.queries import get_match_cond
	
	return webnotes.conn.sql("""select gle.voucher_no, gle.posting_date, 
		gle.%(account_type)s from `tabGL Entry` gle
	    where gle.account = '%(acc)s' 
	    	and gle.voucher_type = '%(dt)s'
			and gle.voucher_no like '%(txt)s'  
	    	and (ifnull(gle.against_voucher, '') = '' 
	    		or ifnull(gle.against_voucher, '') = gle.voucher_no ) 
			and ifnull(gle.%(account_type)s, 0) > 0 
	   		and (select ifnull(abs(sum(ifnull(debit, 0)) - sum(ifnull(credit, 0))), 0) 
				from `tabGL Entry` 
	        	where against_voucher_type = '%(dt)s' 
	        	and against_voucher = gle.voucher_no 
	        	and voucher_no != gle.voucher_no) 
					!= abs(ifnull(gle.debit, 0) - ifnull(gle.credit, 0)
			) 
			%(mcond)s
	    ORDER BY gle.posting_date desc, gle.voucher_no desc 
	    limit %(start)s, %(page_len)s""" % {
			"dt":filters["dt"], 
			"acc":filters["acc"], 
			"account_type": filters['account_type'], 
			'mcond':get_match_cond(doctype, searchfield), 
			'txt': "%%%s%%" % txt, 
			"start": start, 
			"page_len": page_len
		})
