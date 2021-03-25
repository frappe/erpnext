from __future__ import unicode_literals
import unittest
import frappe
import datetime
from frappe.utils import getdate, nowdate, add_days, add_months
from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.projects.doctype.timesheet.test_timesheet import make_salary_structure_for_timesheet, make_timesheet 
from erpnext.projects.doctype.timesheet.timesheet import make_salary_slip, make_sales_invoice
from erpnext.projects.report.profitability.profitability import execute

class TestProfitability(unittest.TestCase):
	@classmethod
	def setUp(self):
		emp = make_employee("test_employee_9@salary.com", company="_Test Company")
		if not frappe.db.exists("Salary Component", "Timesheet Component"):
			frappe.get_doc({"doctype": "Salary Component", "salary_component": "Timesheet Component"}).insert()
		make_salary_structure_for_timesheet(emp, company="_Test Company")
		self.timesheet = make_timesheet(emp, simulate = True, billable=1)
		self.salary_slip = make_salary_slip(self.timesheet.name)
		self.salary_slip.submit()
		self.sales_invoice = make_sales_invoice(self.timesheet.name, '_Test Item', '_Test Customer')
		self.sales_invoice.due_date = nowdate()
		self.sales_invoice.submit()

	def test_profitability(self):
		filters = {
			'company': '_Test Company',
			'start_date': getdate(),
			'end_date': getdate()
		}

		report = execute(filters)
		expected_data = [
			{
				"customer_name": "_Test Customer",
				"title": "test_employee_9@salary.com",
				"grand_total": 100.0,
				"gross_pay": 78100.0,
				"profit": -19425.0,
				"total_billed_hours": 2.0,
				"utilization": 0.25,
				"fractional_cost": 19525.0,
				"total_working_days": 1.0
			}
		]
		for key in ["customer_name","title","grand_total","gross_pay","profit","total_billed_hours","utilization","fractional_cost","total_working_days"]:
			self.assertEqual(expected_data[0].get(key), report[1][0].get(key))

	def tearDown(self):
		frappe.get_doc("Sales Invoice", self.sales_invoice.name).cancel()
		frappe.get_doc("Salary Slip", self.salary_slip.name).cancel()
		frappe.get_doc("Timesheet", self.timesheet.name).cancel()