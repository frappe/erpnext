# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.model.bean import getlist
from webnotes import msgprint

class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def validate(self):
		self.validate_fiscal_year()
		self.validate_exp_details()
			
	def on_submit(self):
		if self.doc.approval_status=="Draft":
			webnotes.msgprint("""Please set Approval Status to 'Approved' or \
				'Rejected' before submitting""", raise_exception=1)
	
	def validate_fiscal_year(self):
		from accounts.utils import validate_fiscal_year
		validate_fiscal_year(self.doc.posting_date, self.doc.fiscal_year, "Posting Date")
			
	def validate_exp_details(self):
		if not getlist(self.doclist, 'expense_voucher_details'):
			msgprint("Please add expense voucher details")
			raise Exception
