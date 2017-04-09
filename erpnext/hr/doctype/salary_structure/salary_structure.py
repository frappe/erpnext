# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

<<<<<<< HEAD
from frappe.utils import flt, cint, getdate
=======
from frappe.utils import cstr, flt, getdate
from frappe.model.naming import make_autoname
>>>>>>> Vhrs Update 12/11/16
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document
from erpnext.hr.utils import set_employee_name

class SalaryStructure(Document):
	def autoname(self):
		self.name = make_autoname(self.employee + '/.SST' + '/.#####')
		
	def validate(self):
		self.check_existing()
		self.validate_amount()
<<<<<<< HEAD
		for e in self.get('employees'):
			set_employee_name(e)
		self.validate_date()
=======
		self.validate_employee()
		self.validate_joining_date()
		set_employee_name(self)

	def get_employee_details(self):
		ret = {}
		det = frappe.db.sql("""select employee_name, branch, designation, department
			from `tabEmployee` where name = %s""", self.employee)
		if det:
			ret = {
				'employee_name': cstr(det[0][0]),
				'branch': cstr(det[0][1]),
				'designation': cstr(det[0][2]),
				'department': cstr(det[0][3]),
				'backup_employee': cstr(self.employee)
			}
		return ret
>>>>>>> Vhrs Update 12/11/16

	def get_ss_values(self,employee):
		basic_info = frappe.db.sql("""select bank_name, bank_ac_no
			from `tabEmployee` where name =%s""", employee)
		ret = {'bank_name': basic_info and basic_info[0][0] or '',
			'bank_ac_no': basic_info and basic_info[0][1] or ''}
		return ret

	def make_table(self, doct_name, tab_fname, tab_name):
		list1 = frappe.db.sql("select name from `tab%s` where docstatus != 2" % doct_name)
		for li in list1:
			child = self.append(tab_fname, {})
			if(tab_fname == 'earnings'):
				child.e_type = cstr(li[0])
				child.modified_value = 0
			elif(tab_fname == 'deductions'):
				child.d_type = cstr(li[0])
				child.d_modified_amt = 0

	def make_earn_ded_table(self):
		self.make_table('Earning Type','earnings','Salary Structure Earning')
		self.make_table('Deduction Type','deductions', 'Salary Structure Deduction')

	def check_existing(self):
		ret = self.get_other_active_salary_structure()

		if ret and self.is_active=='Yes':
			frappe.throw(_("Another Salary Structure {0} is active for employee {1}. Please make its status 'Inactive' to proceed.").format(ret, self.employee))

	def get_other_active_salary_structure(self):
		ret = frappe.db.sql("""select name from `tabSalary Structure` where is_active = 'Yes'
			and employee = %s and name!=%s""", (self.employee,self.name))

		return ret[0][0] if ret else None

	def before_test_insert(self):
		"""Make any existing salary structure for employee inactive."""
		ret = self.get_other_active_salary_structure()
		if ret:
			frappe.db.set_value("Salary Structure", ret, "is_active", "No")

	def validate_amount(self):
		if flt(self.net_pay) < 0:
			frappe.throw(_("Net pay cannot be negative"))

<<<<<<< HEAD
	def validate_date(self):
		for employee in self.get('employees'):
			joining_date, relieving_date = frappe.db.get_value("Employee", employee.employee,
				["date_of_joining", "relieving_date"])
			if employee.from_date and getdate(employee.from_date) < joining_date:
				frappe.throw(_("From Date {0} for Employee {1} cannot be before employee's joining Date {2}")
					    .format(employee.from_date, employee.employee, joining_date))

		st_name = frappe.db.sql("""select parent from `tabSalary Structure Employee`
			where
			employee=%(employee)s
			and (
				(%(from_date)s between from_date and ifnull(to_date, '2199-12-31'))
				or (%(to_date)s between from_date and ifnull(to_date, '2199-12-31'))
				or (from_date between %(from_date)s and %(to_date)s)
			)
			and (
				exists (select name from `tabSalary Structure`
				where name = `tabSalary Structure Employee`.parent and is_active = 'Yes')
			)
			and parent != %(salary_struct)s""",
			{
				'employee': employee.employee,
				'from_date': employee.from_date,
				'to_date': (employee.to_date or '2199-12-31'),
				'salary_struct': self.name
			})

		if st_name:
			frappe.throw(_("Active Salary Structure {0} found for employee {1} for the given dates")
				.format(st_name[0][0], employee.employee))
=======
	def validate_employee(self):
		old_employee = frappe.db.get_value("Salary Structure", self.name, "employee")
		if old_employee and self.employee != old_employee:
			frappe.throw(_("Employee can not be changed"))
			
	def validate_joining_date(self):
		joining_date = getdate(frappe.db.get_value("Employee", self.employee, "date_of_joining"))
		if getdate(self.from_date) < joining_date:
			frappe.throw(_("From Date in Salary Structure cannot be lesser than Employee Joining Date."))
>>>>>>> Vhrs Update 12/11/16

@frappe.whitelist()
def make_salary_slip(source_name, target_doc=None):
	def postprocess(source, target):
<<<<<<< HEAD
		if employee:
			employee_details = frappe.db.get_value("Employee", employee, 
							["employee_name", "branch", "designation", "department"], as_dict=1)
			target.employee = employee
			target.employee_name = employee_details.employee_name
			target.branch = employee_details.branch
			target.designation = employee_details.designation
			target.department = employee_details.department
		target.run_method('process_salary_structure')
=======
		target.run_method("pull_emp_details")
		target.run_method("get_leave_details")
		target.run_method("calculate_net_pay")
>>>>>>> Vhrs Update 12/11/16

	doc = get_mapped_doc("Salary Structure", source_name, {
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
	}, target_doc, postprocess)

<<<<<<< HEAD
	if cint(as_print):
		doc.name = 'Preview for {0}'.format(employee)
		return frappe.get_print(doc.doctype, doc.name, doc = doc, print_format = print_format)
	else:
		return doc


@frappe.whitelist()
def get_employees(**args):
	return frappe.get_list('Employee',filters=args['filters'], fields=['name', 'employee_name'])
=======
	return doc
>>>>>>> Vhrs Update 12/11/16
