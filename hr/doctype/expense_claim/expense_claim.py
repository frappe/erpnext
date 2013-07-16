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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.	If not, see <http://www.gnu.org/licenses/>.

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
