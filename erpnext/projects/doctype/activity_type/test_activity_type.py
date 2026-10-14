# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe

from erpnext.projects.doctype.timesheet.test_timesheet import make_timesheet
from erpnext.setup.doctype.employee.test_employee import make_employee
from erpnext.tests.utils import ERPNextTestSuite


class TestActivityType(ERPNextTestSuite):
	def test_disabled_activity_type_is_refused_on_timesheets(self):
		frappe.db.set_value("Activity Type", "_Test Activity Type", "disabled", 1)
		employee = make_employee("test_employee_6@salary.com", company="_Test Company")
		self.assertRaises(frappe.ValidationError, make_timesheet, employee, simulate=True)

	def test_disabled_activity_type_allows_updates_after_submit(self):
		employee = make_employee("test_employee_6@salary.com", company="_Test Company")
		timesheet = make_timesheet(employee, simulate=True)
		draft = make_timesheet(employee, simulate=True, do_not_submit=True)
		frappe.db.set_value("Activity Type", "_Test Activity Type", "disabled", 1)

		timesheet.title = "_Test Updated Title"
		timesheet.save()
		self.assertRaises(frappe.ValidationError, draft.submit)
