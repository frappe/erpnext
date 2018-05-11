# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import frappe
import unittest

from erpnext.hr.doctype.leave_application.leave_application import LeaveDayBlockedError, OverlapError
from frappe.permissions import clear_user_permissions_for_doctype

test_dependencies = ["Leave Allocation", "Leave Block List"]

_test_records = [
 {
  "company": "_Test Company",
  "doctype": "Leave Application",
  "employee": "_T-Employee-00001",
  "from_date": "2013-05-01",
  "leave_type": "_Test Leave Type",
  "posting_date": "2013-01-02",
  "to_date": "2013-05-05"
 },
 {
  "company": "_Test Company",
  "doctype": "Leave Application",
  "employee": "_T-Employee-00002",
  "from_date": "2013-05-01",
  "leave_type": "_Test Leave Type",
  "posting_date": "2013-01-02",
  "to_date": "2013-05-05"
 },
 {
  "company": "_Test Company",
  "doctype": "Leave Application",
  "employee": "_T-Employee-00001",
  "from_date": "2013-01-15",
  "leave_type": "_Test Leave Type LWP",
  "posting_date": "2013-01-02",
  "to_date": "2013-01-15"
 }
]


class TestLeaveApplication(unittest.TestCase):
	def setUp(self):
		for dt in ["Leave Application", "Leave Allocation", "Salary Slip"]:
			frappe.db.sql("delete from `tab%s`" % dt)

	def tearDown(self):
		frappe.set_user("Administrator")

	def _clear_roles(self):
		frappe.db.sql("""delete from `tabHas Role` where parent in
			("test@example.com", "test1@example.com", "test2@example.com")""")

	def _clear_applications(self):
		frappe.db.sql("""delete from `tabLeave Application`""")

	def get_application(self, doc):
		application = frappe.copy_doc(doc)
		application.from_date = "2013-01-01"
		application.to_date = "2013-01-05"
		return application

	def test_block_list(self):
		self._clear_roles()

		from frappe.utils.user import add_role
		add_role("test1@example.com", "HR User")
		add_role("test1@example.com", "Leave Approver")
		clear_user_permissions_for_doctype("Employee")

		frappe.db.set_value("Department", "_Test Department",
			"leave_block_list", "_Test Leave Block List")

		make_allocation_record()

		application = self.get_application(_test_records[0])
		application.insert()
		application.status = "Approved"
		self.assertRaises(LeaveDayBlockedError, application.submit)

		frappe.set_user("test1@example.com")

		# clear other applications
		frappe.db.sql("delete from `tabLeave Application`")

		application = self.get_application(_test_records[0])
		self.assertTrue(application.insert())

	def test_overlap(self):
		self._clear_roles()
		self._clear_applications()

		from frappe.utils.user import add_role
		add_role("test@example.com", "Employee")
		add_role("test2@example.com", "Leave Approver")

		frappe.set_user("test@example.com")

		make_allocation_record()

		application = self.get_application(_test_records[0])
		application.insert()

		application = self.get_application(_test_records[0])
		self.assertRaises(OverlapError, application.insert)

	def test_overlap_with_half_day_1(self):
		self._clear_roles()
		self._clear_applications()

		from frappe.utils.user import add_role
		add_role("test@example.com", "Employee")
		add_role("test2@example.com", "Leave Approver")

		frappe.set_user("test@example.com")

		make_allocation_record()

		# leave from 1-5, half day on 3rd
		application = self.get_application(_test_records[0])
		application.half_day = 1
		application.half_day_date = "2013-01-03"
		application.insert()

		# Apply again for a half day leave on 3rd
		application = self.get_application(_test_records[0])
		application.from_date = "2013-01-03"
		application.to_date = "2013-01-03"
		application.half_day = 1
		application.half_day_date = "2013-01-03"
		application.insert()

		# Apply again for a half day leave on 3rd
		application = self.get_application(_test_records[0])
		application.from_date = "2013-01-03"
		application.to_date = "2013-01-03"
		application.half_day = 1
		application.half_day_date = "2013-01-03"

		self.assertRaises(OverlapError, application.insert)

	def test_overlap_with_half_day_2(self):
		self._clear_roles()
		self._clear_applications()

		from frappe.utils.user import add_role
		add_role("test@example.com", "Employee")
		add_role("test2@example.com", "Leave Approver")

		frappe.set_user("test@example.com")

		make_allocation_record()

		# leave from 1-5, no half day
		application = self.get_application(_test_records[0])
		application.insert()

		# Apply again for a half day leave on 1st
		application = self.get_application(_test_records[0])
		application.half_day = 1
		application.half_day_date = application.from_date

		self.assertRaises(OverlapError, application.insert)

	def test_overlap_with_half_day_3(self):
		self._clear_roles()
		self._clear_applications()

		from frappe.utils.user import add_role
		add_role("test@example.com", "Employee")
		add_role("test2@example.com", "Leave Approver")

		frappe.set_user("test@example.com")

		make_allocation_record()

		# leave from 1-5, half day on 5th
		application = self.get_application(_test_records[0])
		application.half_day = 1
		application.half_day_date = "2013-01-05"
		application.insert()

		# Apply leave from 4-7, half day on 5th
		application = self.get_application(_test_records[0])
		application.from_date = "2013-01-04"
		application.to_date = "2013-01-07"
		application.half_day = 1
		application.half_day_date = "2013-01-05"

		self.assertRaises(OverlapError, application.insert)

		# Apply leave from 5-7, half day on 5th
		application = self.get_application(_test_records[0])
		application.from_date = "2013-01-05"
		application.to_date = "2013-01-07"
		application.half_day = 1
		application.half_day_date = "2013-01-05"
		application.insert()

	def test_global_block_list(self):
		self._clear_roles()

		from frappe.utils.user import add_role
		add_role("test1@example.com", "Employee")
		add_role("test@example.com", "Leave Approver")

		make_allocation_record(employee="_T-Employee-00002")

		application = self.get_application(_test_records[1])

		frappe.db.set_value("Leave Block List", "_Test Leave Block List",
			"applies_to_all_departments", 1)
		frappe.db.set_value("Employee", "_T-Employee-00002", "department",
			"_Test Department")

		frappe.set_user("test1@example.com")
		application.insert()
		application.status = "Approved"
		frappe.set_user("test@example.com")
		self.assertRaises(LeaveDayBlockedError, application.submit)

		frappe.db.set_value("Leave Block List", "_Test Leave Block List",
			"applies_to_all_departments", 0)

def make_allocation_record(employee=None, leave_type=None):
	frappe.db.sql("delete from `tabLeave Allocation`")

	allocation = frappe.get_doc({
		"doctype": "Leave Allocation",
		"employee": employee or "_T-Employee-00001",
		"leave_type": leave_type or "_Test Leave Type",
		"from_date": "2013-01-01",
		"to_date": "2015-12-31",
		"new_leaves_allocated": 30
	})

	allocation.insert(ignore_permissions=True)
	allocation.submit()