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
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def get_employee_name(self):
		emp_dtl = sql("select employee_name,company_email from `tabEmployee` where name=%s", self.doc.employee)
		emp_nm = emp_dtl and emp_dtl[0][0] or ''
		self.doc.employee_name = emp_nm
		self.doc.email_id = emp_dtl and emp_dtl[0][1] or ''

		return cstr(emp_nm)	
	
	def get_approver_lst(self):
		approver_lst =[]
		approver_lst1 = get_obj('Authorization Control').get_approver_name(self.doc.doctype,0,self)
		if approver_lst1:
			approver_lst=approver_lst1
		else:
			approver_lst = [x[0] for x in sql("select distinct name from `tabProfile` where enabled=1 and name!='Administrator' and name!='Guest' and docstatus!=2")]
		return approver_lst

	def set_approver(self):
		ret={}
		approver_lst =[]
		emp_nm = self.get_employee_name()
		approver_lst = self.get_approver_lst()		
		ret = {'app_lst':"\n" + "\n".join(approver_lst), 'emp_nm':cstr(emp_nm)}
		return ret

	def update_voucher(self):
		sql("delete from `tabExpense Claim Detail` where parent = '%s'"%self.doc.name)
		for d in getlist(self.doclist, 'expense_voucher_details'):
			if not d.expense_type or not d.claim_amount:
				msgprint("Please remove the extra blank row added")
				raise Exception
			d.save(1)
		if self.doc.total_sanctioned_amount:
			set(self.doc,'total_sanctioned_amount',self.doc.total_sanctioned_amount)
		if self.doc.remark:
			set(self.doc, 'remark', self.doc.remark)
	
	def approve_voucher(self):
		for d in getlist(self.doclist, 'expense_voucher_details'):
			if not d.sanctioned_amount:
				msgprint("Please add 'Sanctioned Amount' for all expenses")
				return cstr('Incomplete')
		
		if not self.doc.total_sanctioned_amount:
			msgprint("Please calculate total sanctioned amount using button 'Calculate Total Amount'")
			return cstr('No Amount')
		self.update_voucher()
		
		set(self.doc, 'approval_status', 'Approved')		
		# on approval notification
		#get_obj('Notification Control').notify_contact('Expense Claim Approved', self.doc.doctype, self.doc.name, self.doc.email_id, self.doc.employee_name)

		return cstr('Approved')
	
	def reject_voucher(self):
		
		if self.doc.remark:
			set(self.doc, 'remark', self.doc.remark)	 
		set(self.doc, 'approval_status', 'Rejected')		

		return cstr('Rejected')
	
	
	def validate_fiscal_year(self):
		fy=sql("select year_start_date from `tabFiscal Year` where name='%s'"%self.doc.fiscal_year)
		ysd=fy and fy[0][0] or ""
		yed=add_days(str(ysd),365)
		if str(self.doc.posting_date) < str(ysd) or str(self.doc.posting_date) > str(yed):
			msgprint("Posting Date is not within the Fiscal Year selected")
			raise Exception
		
	def validate(self):
		self.validate_fiscal_year()
	
	def on_update(self):
		set(self.doc, 'approval_status', 'Draft')
	
	def validate_exp_details(self):
		if not getlist(self.doclist, 'expense_voucher_details'):
			msgprint("Please add expense voucher details")
			raise Exception
		
		if not self.doc.total_claimed_amount:
			msgprint("Please calculate Total Claimed Amount")
			raise Exception
		
		if not self.doc.exp_approver:
			msgprint("Please select Expense Claim approver")
			raise Exception
		
	def on_submit(self):
		self.validate_exp_details()
		set(self.doc, 'approval_status', 'Submitted')
	
	def on_cancel(self):
		set(self.doc, 'approval_status', 'Cancelled')

	def get_formatted_message(self, args):
		""" get formatted message for auto notification"""
		return get_obj('Notification Control').get_formatted_message(args)
