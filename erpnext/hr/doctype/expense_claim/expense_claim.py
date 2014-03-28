# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.model.bean import getlist
from frappe import _

from frappe.model.document import Document

class ExpenseClaim(Document):

	def validate(self):
		self.validate_fiscal_year()
		self.validate_exp_details()
			
	def on_submit(self):
		if self.approval_status=="Draft":
			frappe.msgprint("""Please set Approval Status to 'Approved' or \
				'Rejected' before submitting""", raise_exception=1)
	
	def validate_fiscal_year(self):
		from erpnext.accounts.utils import validate_fiscal_year
		validate_fiscal_year(self.posting_date, self.fiscal_year, "Posting Date")
			
	def validate_exp_details(self):
		if not self.get('expense_voucher_details'):
			frappe.throw(_("Please add expense voucher details"))
