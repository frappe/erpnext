# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
import erpnext
from frappe.utils.make_random import get_random
from frappe.utils import nowdate, add_days, add_years, getdate, add_months
from erpnext.hr.doctype.salary_structure.salary_structure import make_salary_slip
from erpnext.hr.doctype.salary_slip.test_salary_slip import make_earning_salary_component,\
	make_deduction_salary_component, make_employee_salary_slip
from erpnext.hr.doctype.employee.test_employee import make_employee


test_dependencies = ["Fiscal Year"]

class TestSalaryStructure(unittest.TestCase):
	def setUp(self):
		for dt in ["Salary Slip", "Salary Structure", "Salary Structure Assignment"]:
			frappe.db.sql("delete from `tab%s`" % dt)

		self.make_holiday_list()
		frappe.db.set_value("Company", erpnext.get_default_company(), "default_holiday_list", "Salary Structure Test Holiday List")
		make_employee("test_employee@salary.com")
		make_employee("test_employee_2@salary.com")


	def make_holiday_list(self):
		if not frappe.db.get_value("Holiday List", "Salary Structure Test Holiday List"):
			holiday_list = frappe.get_doc({
				"doctype": "Holiday List",
				"holiday_list_name": "Salary Structure Test Holiday List",
				"from_date": nowdate(),
				"to_date": add_years(nowdate(), 1),
				"weekly_off": "Sunday"
			}).insert()
			holiday_list.get_weekly_off_dates()
			holiday_list.save()

	def test_amount_totals(self):
		sal_slip = frappe.get_value("Salary Slip", {"employee_name":"test_employee_2@salary.com"})
		if not sal_slip:
			sal_slip = make_employee_salary_slip("test_employee_2@salary.com", "Monthly", "Salary Structure Sample")
			self.assertEqual(sal_slip.get("salary_structure"), 'Salary Structure Sample')
			self.assertEqual(sal_slip.get("earnings")[0].amount, 25000)
			self.assertEqual(sal_slip.get("earnings")[1].amount, 3000)
			self.assertEqual(sal_slip.get("earnings")[2].amount, 12500)
			self.assertEqual(sal_slip.get("gross_pay"), 40500)
			self.assertEqual(sal_slip.get("deductions")[0].amount, 5000)
			self.assertEqual(sal_slip.get("deductions")[1].amount, 5000)
			self.assertEqual(sal_slip.get("total_deduction"), 10000)
			self.assertEqual(sal_slip.get("net_pay"), 30500)

	def test_whitespaces_in_formula_conditions_fields(self):
		salary_structure = make_salary_structure("Salary Structure Sample", "Monthly", dont_submit=True)

		for row in salary_structure.earnings:
			row.formula = "\n%s\n\n"%row.formula
			row.condition = "\n%s\n\n"%row.condition

		for row in salary_structure.deductions:
			row.formula = "\n%s\n\n"%row.formula
			row.condition = "\n%s\n\n"%row.condition

		salary_structure.save()

		for row in salary_structure.earnings:
			self.assertFalse("\n" in row.formula or "\n" in row.condition)

		for row in salary_structure.deductions:
			self.assertFalse(("\n" in row.formula) or ("\n" in row.condition))

	def test_salary_structures_assignment(self):
		salary_structure = make_salary_structure("Salary Structure Sample", "Monthly")
		employee = "test_assign_stucture@salary.com"
		employee_doc_name = make_employee(employee)
		# clear the already assigned stuctures
		frappe.db.sql('''delete from `tabSalary Structure Assignment` where employee=%s and salary_structure=%s ''',
					  ("test_assign_stucture@salary.com",salary_structure.name))
		#test structure_assignment
		salary_structure.assign_salary_structure(employee=employee_doc_name,from_date='2013-01-01',base=5000,variable=200)
		salary_structure_assignment = frappe.get_doc("Salary Structure Assignment",{'employee':employee_doc_name, 'from_date':'2013-01-01'})
		self.assertEqual(salary_structure_assignment.docstatus, 1)
		self.assertEqual(salary_structure_assignment.base, 5000)
		self.assertEqual(salary_structure_assignment.variable, 200)

def make_salary_structure(salary_structure, payroll_frequency, employee=None, dont_submit=False, other_details=None, test_tax=False, company=None):
	if test_tax:
		frappe.db.sql("""delete from `tabSalary Structure` where name=%s""",(salary_structure))
	if not frappe.db.exists('Salary Structure', salary_structure):
		details = {
			"doctype": "Salary Structure",
			"name": salary_structure,
			"company": company or "_Test Company",
			"earnings": make_earning_salary_component(test_tax=test_tax),
			"deductions": make_deduction_salary_component(test_tax=test_tax),
			"payroll_frequency": payroll_frequency,
			"payment_account": get_random("Account")
		}
		if other_details and isinstance(other_details, dict):
			details.update(other_details)
		salary_structure_doc = frappe.get_doc(details).insert()
		if not dont_submit:
			salary_structure_doc.submit()
	else:
		salary_structure_doc = frappe.get_doc("Salary Structure", salary_structure)

	if employee and not frappe.db.get_value("Salary Structure Assignment",
		{'employee':employee, 'docstatus': 1}) and salary_structure_doc.docstatus==1:
			create_salary_structure_assignment(employee, salary_structure)

	return salary_structure_doc

def create_salary_structure_assignment(employee, salary_structure, from_date=None):
	if frappe.db.exists("Salary Structure Assignment", {"employee": employee}):
		frappe.db.sql("""delete from `tabSalary Structure Assignment` where employee=%s""",(employee))
	salary_structure_assignment = frappe.new_doc("Salary Structure Assignment")
	salary_structure_assignment.employee = employee
	salary_structure_assignment.base = 50000
	salary_structure_assignment.variable = 5000
	salary_structure_assignment.from_date = from_date or add_months(nowdate(), -1)
	salary_structure_assignment.salary_structure = salary_structure
	salary_structure_assignment.company = erpnext.get_default_company()
	salary_structure_assignment.save(ignore_permissions=True)
	salary_structure_assignment.submit()
	return salary_structure_assignment
