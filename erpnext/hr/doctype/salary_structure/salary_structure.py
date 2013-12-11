# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cstr, flt
from webnotes.model.doc import addchild, make_autoname
from webnotes import msgprint, _


class DocType:
	def __init__(self,doc,doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def autoname(self):
		self.doc.name = make_autoname(self.doc.employee + '/.SST' + '/.#####')

	def get_employee_details(self):
		ret = {}
		det = webnotes.conn.sql("""select employee_name, branch, designation, department, grade 
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
		basic_info = webnotes.conn.sql("""select bank_name, bank_ac_no, esic_card_no, pf_number 
			from `tabEmployee` where name =%s""", employee)
		ret = {'bank_name': basic_info and basic_info[0][0] or '',
			'bank_ac_no': basic_info and basic_info[0][1] or '',
			'esic_no': basic_info and basic_info[0][2] or '',
			'pf_no': basic_info and basic_info[0][3] or ''}
		return ret

	def make_table(self, doct_name, tab_fname, tab_name):
		list1 = webnotes.conn.sql("select name from `tab%s` where docstatus != 2" % doct_name)
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
		ret = webnotes.conn.sql("""select name from `tabSalary Structure` where is_active = 'Yes' 
			and employee = %s and name!=%s""", (self.doc.employee,self.doc.name))
		if ret and self.doc.is_active=='Yes':
			msgprint(_("""Another Salary Structure '%s' is active for employee '%s'. 
				Please make its status 'Inactive' to proceed.""") % 
				(cstr(ret), self.doc.employee), raise_exception=1)

	def validate_amount(self):
		if flt(self.doc.net_pay) < 0:
			msgprint(_("Net pay can not be negative"), raise_exception=1)

	def validate(self):	 
		self.check_existing()
		self.validate_amount()
		
@webnotes.whitelist()
def make_salary_slip(source_name, target_doclist=None):
	from webnotes.model.mapper import get_mapped_doclist
	
	def postprocess(source, target):
		sal_slip = webnotes.bean(target)
		sal_slip.run_method("pull_emp_details")
		sal_slip.run_method("get_leave_details")
		sal_slip.run_method("calculate_net_pay")

	doclist = get_mapped_doclist("Salary Structure", source_name, {
		"Salary Structure": {
			"doctype": "Salary Slip", 
			"field_map": {
				"total_earning": "gross_pay"
			}
		}, 
		"Salary Structure Deduction": {
			"doctype": "Salary Slip Deduction", 
			"field_map": [
				["depend_on_lwp", "d_depends_on_lwp"],
				["d_modified_amt", "d_amount"],
				["d_modified_amt", "d_modified_amount"]
			],
			"add_if_empty": True
		}, 
		"Salary Structure Earning": {
			"doctype": "Salary Slip Earning", 
			"field_map": [
				["depend_on_lwp", "e_depends_on_lwp"], 
				["modified_value", "e_modified_amount"],
				["modified_value", "e_amount"]
			],
			"add_if_empty": True
		}
	}, target_doclist, postprocess)

	return [d.fields for d in doclist]