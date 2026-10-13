# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.projects.doctype.timesheet.test_timesheet import make_timesheet
from erpnext.setup.doctype.employee.test_employee import make_employee
from erpnext.tests.utils import ERPNextTestSuite


class TestProjectsSettings(ERPNextTestSuite):
	@ERPNextTestSuite.change_settings("Projects Settings", {"fetch_timesheet_in_sales_invoice": 1})
	def test_cleared_timesheets_are_not_fetched_again(self):
		employee = make_employee("test_employee_6@salary.com", company="_Test Company")
		project = frappe.get_value("Project", {"project_name": "_Test Project"})
		make_timesheet(employee, simulate=True, is_billable=1, project=project, company="_Test Company")

		sales_invoice = create_sales_invoice(do_not_save=True)
		sales_invoice.project = project
		sales_invoice.insert()
		self.assertTrue(sales_invoice.timesheets)

		sales_invoice.set("timesheets", [])
		sales_invoice.save()
		self.assertFalse(sales_invoice.timesheets)
