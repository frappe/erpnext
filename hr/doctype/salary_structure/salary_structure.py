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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.	If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cstr, flt
from webnotes.model.doc import addchild, make_autoname
from webnotes import msgprint, _

sql = webnotes.conn.sql
	


class DocType:
	def __init__(self,doc,doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def autoname(self):
		self.doc.name = make_autoname(self.doc.employee + '/.SST' + '/.#####')

	def get_employee_details(self):
		ret = {}
		det = sql("""select employee_name, branch, designation, department, grade 
			from `tabEmployee` where name = %s""", self.doc.employee)
		if det:
			ret = {
				'employee_name': cstr(det[0][0]),
				'branch': cstr(det[0][1]),
				'designation': cstr(det[0][2]),
				'department': cstr(det[0][3]),
				'grade': cstr(det[0][4]),
				'backup_employee': cstr(self.doc.employee)
			}
		return ret

	def get_ss_values(self,employee):
		basic_info = sql("""select bank_name, bank_ac_no, esic_card_no, pf_number 
			from `tabEmployee` where name =%s""", employee)
		ret = {'bank_name': basic_info and basic_info[0][0] or '',
			'bank_ac_no': basic_info and basic_info[0][1] or '',
			'esic_no': basic_info and basic_info[0][2] or '',
			'pf_no': basic_info and basic_info[0][3] or ''}
		return ret

	def make_table(self, doct_name, tab_fname, tab_name):
		list1 = sql("select name from `tab%s` where docstatus != 2" % doct_name)
		for li in list1:
			child = addchild(self.doc, tab_fname, tab_name, self.doclist)
			if(tab_fname == 'earning_details'):
				child.e_type = cstr(li[0])
				child.modified_value = 0
			elif(tab_fname == 'deduction_details'):
				child.d_type = cstr(li[0])
				child.d_modified_amt = 0
			 
	def make_earn_ded_table(self):					 
		self.make_table('Earning Type','earning_details','Salary Structure Earning')
		self.make_table('Deduction Type','deduction_details', 'Salary Structure Deduction')

	def check_existing(self):
		ret = sql("""select name from `tabSalary Structure` where is_active = 'Yes' 
			and employee = %s and name!=%s""", (self.doc.employee,self.doc.name))
		if ret and self.doc.is_active=='Yes':
			msgprint(_("""Another Salary Structure '%s' is active for employee '%s'. 
				Please make its status 'Inactive' to proceed.""") % 
				(cstr(ret), self.doc.employee), raise_exception=1)

	def validate_amount(self):
		if flt(self.doc.ctc) < 12*flt(self.doc.total_earning):
			msgprint(_("Annual Cost To Company can not be less than 12 months of Total Earning"), 
				raise_exception=1)
				
		if flt(self.doc.net_pay) < 0:
			msgprint(_("Net pay can not be negative"), raise_exception=1)
		elif flt(self.doc.net_pay)*12 > flt(self.doc.ctc):
			msgprint(_("Net pay can not be greater than 1/12th of Annual Cost To Company"), 
				raise_exception=1)
		

	def validate(self):	 
		self.check_existing()
		self.validate_amount()