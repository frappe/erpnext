# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.projects.doctype.timesheet.test_timesheet import make_timesheet
from erpnext.setup.doctype.employee.test_employee import make_employee

test_records = frappe.get_test_records("Activity Type")


class TestActivityType(FrappeTestCase):
	def test_disabled_activity_type_is_refused_on_timesheets(self):
		frappe.db.set_value("Activity Type", "_Test Activity Type", "disabled", 1)
		employee = make_employee("test_employee_6@salary.com", company="_Test Company")
		self.assertRaises(frappe.ValidationError, make_timesheet, employee, simulate=True)
