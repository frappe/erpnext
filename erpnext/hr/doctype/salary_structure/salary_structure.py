# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import flt, cint, getdate
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document
from erpnext.hr.utils import set_employee_name

class SalaryStructure(Document):
	
	def validate(self):
		self.validate_amount()
		for e in self.get('employees'):
			set_employee_name(e)
		self.validate_date()

	def get_ss_values(self,employee):
		basic_info = frappe.db.sql("""select bank_name, bank_ac_no
			from `tabEmployee` where name =%s""", employee)
		ret = {'bank_name': basic_info and basic_info[0][0] or '',
			'bank_ac_no': basic_info and basic_info[0][1] or ''}
		return ret

	def validate_amount(self):
		if flt(self.net_pay) < 0 and self.salary_slip_based_on_timesheet:
			frappe.throw(_("Net pay cannot be negative"))

	def validate_date(self):
		for employee in self.get('employees'):
			joining_date, relieving_date = frappe.db.get_value("Employee", employee.employee,
				["date_of_joining", "relieving_date"])

			if employee.from_date and joining_date and getdate(employee.from_date) < joining_date:
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

@frappe.whitelist()
def make_salary_slip(source_name, target_doc = None, employee = None, as_print = False, print_format = None):
	def postprocess(source, target):
		if employee:
			employee_details = frappe.db.get_value("Employee", employee, 
							["employee_name", "branch", "designation", "department"], as_dict=1)
			target.employee = employee
			target.employee_name = employee_details.employee_name
			target.branch = employee_details.branch
			target.designation = employee_details.designation
			target.department = employee_details.department
		target.run_method('process_salary_structure')

	doc = get_mapped_doc("Salary Structure", source_name, {
		"Salary Structure": {
			"doctype": "Salary Slip",
			"field_map": {
				"total_earning": "gross_pay",
				"name": "salary_structure"
			}
		}
	}, target_doc, postprocess, ignore_child_tables=True)

	if cint(as_print):
		doc.name = 'Preview for {0}'.format(employee)
		return frappe.get_print(doc.doctype, doc.name, doc = doc, print_format = print_format)
	else:
		return doc


@frappe.whitelist()
def get_employees(**args):
	return frappe.get_list('Employee',filters=args['filters'], fields=['name', 'employee_name'])
