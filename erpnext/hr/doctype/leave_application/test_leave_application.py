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
  "employee": "_T-Employee-0001",
  "from_date": "2013-05-01",
  "leave_type": "_Test Leave Type",
  "posting_date": "2013-01-02",
  "to_date": "2013-05-05"
 },
 {
  "company": "_Test Company",
  "doctype": "Leave Application",
  "employee": "_T-Employee-0002",
  "from_date": "2013-05-01",
  "leave_type": "_Test Leave Type",
  "posting_date": "2013-01-02",
  "to_date": "2013-05-05"
 },
 {
  "company": "_Test Company",
  "doctype": "Leave Application",
  "employee": "_T-Employee-0001",
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

		# so that this test doesn't affect other tests
		frappe.db.sql("""delete from `tabEmployee Leave Approver`""")

	def _clear_roles(self):
		frappe.db.sql("""delete from `tabHas Role` where parent in
			("test@example.com", "test1@example.com", "test2@example.com")""")

	def _clear_applications(self):
		frappe.db.sql("""delete from `tabLeave Application`""")

	def _add_employee_leave_approver(self, employee, leave_approver):
		temp_session_user = frappe.session.user
		frappe.set_user("Administrator")
		employee = frappe.get_doc("Employee", employee)
		employee.append("leave_approvers", {
			"doctype": "Employee Leave Approver",
			"leave_approver": leave_approver
		})
		employee.save()
		frappe.set_user(temp_session_user)

	def _remove_employee_leave_approver(self, employee, leave_approver):
		temp_session_user = frappe.session.user
		frappe.set_user("Administrator")
		employee = frappe.get_doc("Employee", employee)
		d = employee.get("leave_approvers", {
			"leave_approver": leave_approver
		})
		if d:
			employee.get("leave_approvers").remove(d[0])
			employee.save()
		frappe.set_user(temp_session_user)

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
		application.leave_approver = "test2@example.com"
		application.insert()

		application = self.get_application(_test_records[0])
		application.leave_approver = "test2@example.com"
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
		application.leave_approver = "test2@example.com"
		application.half_day = 1
		application.half_day_date = "2013-01-03"
		application.insert()

		# Apply again for a half day leave on 3rd
		application = self.get_application(_test_records[0])
		application.leave_approver = "test2@example.com"
		application.from_date = "2013-01-03"
		application.to_date = "2013-01-03"
		application.half_day = 1
		application.half_day_date = "2013-01-03"
		application.insert()

		# Apply again for a half day leave on 3rd
		application = self.get_application(_test_records[0])
		application.leave_approver = "test2@example.com"
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
		application.leave_approver = "test2@example.com"
		application.insert()

		# Apply again for a half day leave on 1st
		application = self.get_application(_test_records[0])
		application.leave_approver = "test2@example.com"
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
		application.leave_approver = "test2@example.com"
		application.half_day = 1
		application.half_day_date = "2013-01-05"
		application.insert()
		
		# Apply leave from 4-7, half day on 5th
		application = self.get_application(_test_records[0])
		application.leave_approver = "test2@example.com"
		application.from_date = "2013-01-04"
		application.to_date = "2013-01-07"
		application.half_day = 1
		application.half_day_date = "2013-01-05"
		
		self.assertRaises(OverlapError, application.insert)

		# Apply leave from 5-7, half day on 5th
		application = self.get_application(_test_records[0])
		application.leave_approver = "test2@example.com"
		application.from_date = "2013-01-05"
		application.to_date = "2013-01-07"
		application.half_day = 1
		application.half_day_date = "2013-01-05"
		application.insert()

	def _test_leave_approval_basic_case(self):
		self._clear_applications()

		self._add_employee_leave_approver("_T-Employee-0001", "test1@example.com")

		# create leave application as Employee
		frappe.set_user("test@example.com")

		make_allocation_record()

		application = self.get_application(_test_records[0])
		application.leave_approver = "test1@example.com"
		application.insert()

		# submit leave application by Leave Approver
		frappe.set_user("test1@example.com")
		application.status = "Approved"
		del application._has_access_to
		application.submit()
		self.assertEqual(frappe.db.get_value("Leave Application", application.name,
			"docstatus"), 1)

	def _test_leave_approval_invalid_leave_approver_insert(self):
		from erpnext.hr.doctype.leave_application.leave_application import InvalidLeaveApproverError

		self._clear_applications()

		# add a different leave approver in the employee's list
		# should raise exception if not a valid leave approver
		self._add_employee_leave_approver("_T-Employee-0001", "test2@example.com")
		self._remove_employee_leave_approver("_T-Employee-0001", "test1@example.com")

		make_allocation_record()

		application = self.get_application(_test_records[0])
		frappe.set_user("test@example.com")

		application.leave_approver = "test1@example.com"
		self.assertRaises(InvalidLeaveApproverError, application.insert)

		frappe.db.sql("""delete from `tabEmployee Leave Approver` where parent=%s""",
			"_T-Employee-0001")

	def _test_leave_approval_invalid_leave_approver_submit(self):
		self._clear_applications()
		self._add_employee_leave_approver("_T-Employee-0001", "test2@example.com")

		# create leave application as employee
		# but submit as invalid leave approver - should raise exception
		frappe.set_user("test@example.com")

		make_allocation_record()

		application = self.get_application(_test_records[0])
		application.leave_approver = "test2@example.com"
		application.insert()
		frappe.set_user("test1@example.com")
		del application._has_access_to
		application.status = "Approved"

		from erpnext.hr.doctype.leave_application.leave_application import LeaveApproverIdentityError
		self.assertRaises(LeaveApproverIdentityError, application.submit)

		frappe.db.sql("""delete from `tabEmployee Leave Approver` where parent=%s""",
			"_T-Employee-0001")

	def _test_leave_approval_valid_leave_approver_insert(self):
		self._clear_applications()
		self._add_employee_leave_approver("_T-Employee-0001", "test2@example.com")

		original_department = frappe.db.get_value("Employee", "_T-Employee-0001", "department")
		frappe.db.set_value("Employee", "_T-Employee-0001", "department", None)

		frappe.set_user("test@example.com")

		make_allocation_record()

		application = self.get_application(_test_records[0])
		application.leave_approver = "test2@example.com"
		application.insert()

		# change to valid leave approver and try to submit leave application
		frappe.set_user("test2@example.com")
		application.status = "Approved"
		del application._has_access_to
		application.submit()
		self.assertEqual(frappe.db.get_value("Leave Application", application.name,
			"docstatus"), 1)

		frappe.db.sql("""delete from `tabEmployee Leave Approver` where parent=%s""",
			"_T-Employee-0001")

		frappe.db.set_value("Employee", "_T-Employee-0001", "department", original_department)

def make_allocation_record(employee=None, leave_type=None):
	frappe.db.sql("delete from `tabLeave Allocation`")

	allocation = frappe.get_doc({
		"doctype": "Leave Allocation",
		"employee": employee or "_T-Employee-0001",
		"leave_type": leave_type or "_Test Leave Type",
		"from_date": "2013-01-01",
		"to_date": "2015-12-31",
		"new_leaves_allocated": 30
	})

	allocation.insert(ignore_permissions=True)
	allocation.submit()
