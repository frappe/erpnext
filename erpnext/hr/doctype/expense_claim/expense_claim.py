# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.model.bean import getlist
from webnotes import msgprint, throw, _

class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def validate(self):
		self.validate_exp_details()

	def on_submit(self):
		if self.doc.approval_status=="Draft":
			throw(_("Please set Approval Status to 'Approved' or 'Rejected' before submitting"))

	def validate_exp_details(self):
		if not getlist(self.doclist, 'expense_voucher_details'):
			throw(_("Please add expense voucher details"))