import unittest

import frappe
from frappe.utils import getdate

from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.payroll.doctype.employee_tax_exemption_declaration.test_employee_tax_exemption_declaration import (
	create_payroll_period,
)
from erpnext.payroll.doctype.salary_slip.test_salary_slip import (
	create_exemption_declaration,
	create_salary_slips_for_payroll_period,
	create_tax_slab,
)
from erpnext.payroll.doctype.salary_structure.test_salary_structure import make_salary_structure
from erpnext.payroll.report.income_tax_computation.income_tax_computation import execute


class TestIncomeTaxComputation(unittest.TestCase):
	def setUp(self):
		self.cleanup_records()
		self.create_records()

	def tearDown(self):
		frappe.db.rollback()

	def cleanup_records(self):
		frappe.db.sql("delete from `tabEmployee Tax Exemption Declaration`")
		frappe.db.sql("delete from `tabPayroll Period`")
		frappe.db.sql("delete from `tabIncome Tax Slab`")
		frappe.db.sql("delete from `tabSalary Component`")
		frappe.db.sql("delete from `tabEmployee Benefit Application`")
		frappe.db.sql("delete from `tabEmployee Benefit Claim`")
		frappe.db.sql("delete from `tabEmployee` where company='_Test Company'")
		frappe.db.sql("delete from `tabSalary Slip`")

	def create_records(self):
		self.employee = make_employee(
			"employee_tax_computation@example.com",
			company="_Test Company",
			date_of_joining=getdate("01-10-2021"),
		)

		self.payroll_period = create_payroll_period(
			name="_Test Payroll Period 1", company="_Test Company"
		)

		self.income_tax_slab = create_tax_slab(
			self.payroll_period,
			allow_tax_exemption=True,
			effective_date=getdate("2019-04-01"),
			company="_Test Company",
		)
		salary_structure = make_salary_structure(
			"Monthly Salary Structure Test Income Tax Computation",
			"Monthly",
			employee=self.employee,
			company="_Test Company",
			currency="INR",
			payroll_period=self.payroll_period,
			test_tax=True,
		)

		create_exemption_declaration(self.employee, self.payroll_period.name)

		create_salary_slips_for_payroll_period(
			self.employee, salary_structure.name, self.payroll_period, deduct_random=False, num=3
		)

	def test_report(self):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"payroll_period": self.payroll_period.name,
				"employee": self.employee,
			}
		)

		result = execute(filters)

		expected_data = {
			"employee": self.employee,
			"employee_name": "employee_tax_computation@example.com",
			"department": "All Departments",
			"income_tax_slab": self.income_tax_slab,
			"ctc": 936000.0,
			"professional_tax": 2400.0,
			"standard_tax_exemption": 50000,
			"total_exemption": 52400.0,
			"total_taxable_amount": 883600.0,
			"applicable_tax": 92789.0,
			"total_tax_deducted": 17997.0,
			"payable_tax": 74792,
		}

		for key, val in expected_data.items():
			self.assertEqual(result[1][0].get(key), val)

		# Run report considering tax exemption declaration
		filters.consider_tax_exemption_declaration = 1

		result = execute(filters)

		expected_data.update(
			{
				"_test_category": 100000.0,
				"total_exemption": 152400.0,
				"total_taxable_amount": 783600.0,
				"applicable_tax": 71989.0,
				"payable_tax": 53992.0,
			}
		)

		for key, val in expected_data.items():
			self.assertEqual(result[1][0].get(key), val)
