# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.projects.doctype.timesheet.test_timesheet import make_timesheet
from erpnext.projects.report.timesheet_billing_summary.timesheet_billing_summary import execute
from erpnext.setup.doctype.employee.test_employee import make_employee
from erpnext.tests.utils import ERPNextTestSuite


class TestTimesheetBillingSummary(ERPNextTestSuite):
	def setUp(self):
		self.employee = make_employee("timesheet_billing@example.com", company="_Test Company")
		self.project = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"_Test TBS {frappe.generate_hash(length=6)}",
				"company": "_Test Company",
			}
		).insert()

	def run_report(self, **extra):
		filters = frappe._dict({"company": "_Test Company", "employee": self.employee})
		filters.update(extra)
		return execute(filters)[1]

	def test_billing_amount_in_company_currency(self):
		ts = make_timesheet(
			self.employee, simulate=True, is_billable=1, project=self.project.name, exchange_rate=2
		)

		row = next(r for r in self.run_report() if r.get("timesheet") == ts.name)
		self.assertEqual(row["billing_amount"], ts.time_logs[0].billing_amount * 2)
