import unittest

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate

from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.projects.doctype.timesheet.test_timesheet import (
	make_salary_structure_for_timesheet,
	make_timesheet,
)
from erpnext.projects.doctype.timesheet.timesheet import make_salary_slip, make_sales_invoice
from erpnext.projects.report.project_profitability.project_profitability import execute


class TestProjectProfitability(FrappeTestCase):
	def setUp(self):
		frappe.db.sql("delete from `tabTimesheet`")
		emp = make_employee("test_employee_9@salary.com", company="_Test Company")

		if not frappe.db.exists("Salary Component", "Timesheet Component"):
			frappe.get_doc(
				{"doctype": "Salary Component", "salary_component": "Timesheet Component"}
			).insert()

		make_salary_structure_for_timesheet(emp, company="_Test Company")
		date = getdate()

		self.timesheet = make_timesheet(emp, is_billable=1)
		self.salary_slip = make_salary_slip(self.timesheet.name)
		self.salary_slip.start_date = self.timesheet.start_date

		holidays = self.salary_slip.get_holidays_for_employee(date, date)
		if holidays:
			frappe.db.set_value("Payroll Settings", None, "include_holidays_in_total_working_days", 1)

		self.salary_slip.submit()
		self.sales_invoice = make_sales_invoice(self.timesheet.name, "_Test Item", "_Test Customer")
		self.sales_invoice.due_date = date
		self.sales_invoice.submit()

		frappe.db.set_value("HR Settings", None, "standard_working_hours", 8)
		frappe.db.set_value("Payroll Settings", None, "include_holidays_in_total_working_days", 0)

	def test_project_profitability(self):
		filters = {
			"company": "_Test Company",
			"start_date": add_days(self.timesheet.start_date, -3),
			"end_date": self.timesheet.start_date,
		}

		report = execute(filters)

		row = report[1][0]
		timesheet = frappe.get_doc("Timesheet", self.timesheet.name)

		self.assertEqual(self.sales_invoice.customer, row.customer_name)
		self.assertEqual(timesheet.title, row.employee_name)
		self.assertEqual(self.sales_invoice.base_grand_total, row.base_grand_total)
		self.assertEqual(self.salary_slip.base_gross_pay, row.base_gross_pay)
		self.assertEqual(timesheet.total_billed_hours, row.total_billed_hours)
		self.assertEqual(self.salary_slip.total_working_days, row.total_working_days)

		standard_working_hours = frappe.db.get_single_value("HR Settings", "standard_working_hours")
		utilization = timesheet.total_billed_hours / (
			self.salary_slip.total_working_days * standard_working_hours
		)
		self.assertEqual(utilization, row.utilization)

		profit = self.sales_invoice.base_grand_total - self.salary_slip.base_gross_pay * utilization
		self.assertEqual(profit, row.profit)

		fractional_cost = self.salary_slip.base_gross_pay * utilization
		self.assertEqual(fractional_cost, row.fractional_cost)
