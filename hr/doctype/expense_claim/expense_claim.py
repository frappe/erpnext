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

from webnotes.utils import add_days
from webnotes.model.bean import getlist
from webnotes import form, msgprint
from webnotes.model.code import get_obj

sql = webnotes.conn.sql

class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def validate(self):
		# if self.doc.exp_approver == self.doc.owner:
		# 	webnotes.msgprint("""Self Approval is not allowed.""", raise_exception=1)
		self.validate_fiscal_year()
		self.validate_exp_details()
			
	def on_submit(self):
		if self.doc.approval_status=="Draft":
			webnotes.msgprint("""Please set Approval Status to 'Approved' or \
				'Rejected' before submitting""", raise_exception=1)
	
	def validate_fiscal_year(self):
		fy=sql("select year_start_date from `tabFiscal Year` where name='%s'"%self.doc.fiscal_year)
		ysd=fy and fy[0][0] or ""
		yed=add_days(str(ysd),365)
		if str(self.doc.posting_date) < str(ysd) or str(self.doc.posting_date) > str(yed):
			msgprint("Posting Date is not within the Fiscal Year selected")
			raise Exception
			
	def validate_exp_details(self):
		if not getlist(self.doclist, 'expense_voucher_details'):
			msgprint("Please add expense voucher details")
			raise Exception
		
@webnotes.whitelist()
def get_approver_list():
	roles = [r[0] for r in webnotes.conn.sql("""select distinct parent from `tabUserRole`
		where role='Expense Approver'""")]
	if not roles:
		webnotes.msgprint("No Expense Approvers. Please assign 'Expense Approver' \
			Role to atleast one user.")
	return roles
