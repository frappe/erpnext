# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

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
  "fiscal_year": "_Test Fiscal Year 2013",
  "from_date": "2013-05-01",
  "leave_type": "_Test Leave Type",
  "posting_date": "2013-01-02",
  "to_date": "2013-05-05"
 },
 {
  "company": "_Test Company",
  "doctype": "Leave Application",
  "employee": "_T-Employee-0002",
  "fiscal_year": "_Test Fiscal Year 2013",
  "from_date": "2013-05-01",
  "leave_type": "_Test Leave Type",
  "posting_date": "2013-01-02",
  "to_date": "2013-05-05"
 },
 {
  "company": "_Test Company",
  "doctype": "Leave Application",
  "employee": "_T-Employee-0001",
  "fiscal_year": "_Test Fiscal Year 2013",
  "from_date": "2013-01-15",
  "leave_type": "_Test Leave Type LWP",
  "posting_date": "2013-01-02",
  "to_date": "2013-01-15"
 }
]


class TestLeaveApplication(unittest.TestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

		# so that this test doesn't affect other tests
		frappe.db.sql("""delete from `tabEmployee Leave Approver`""")

	def _clear_roles(self):
		frappe.db.sql("""delete from `tabUserRole` where parent in
			("test@example.com", "test1@example.com", "test2@example.com")""")

	def _clear_applications(self):
		frappe.db.sql("""delete from `tabLeave Application`""")

	def _add_employee_leave_approver(self, employee, leave_approver):
		temp_session_user = frappe.session.user
		frappe.set_user("Administrator")
		employee = frappe.get_doc("Employee", employee)
		employee.append("employee_leave_approvers", {
			"doctype": "Employee Leave Approver",
			"leave_approver": leave_approver
		})
		employee.save()
		frappe.set_user(temp_session_user)

	def _remove_employee_leave_approver(self, employee, leave_approver):
		temp_session_user = frappe.session.user
		frappe.set_user("Administrator")
		employee = frappe.get_doc("Employee", employee)
		d = employee.get("employee_leave_approvers", {
			"leave_approver": leave_approver
		})
		if d:
			employee.get("employee_leave_approvers").remove(d[0])
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
		application = self.get_application(_test_records[0])
		application.leave_approver = "test2@example.com"
		application.insert()

		application = self.get_application(_test_records[0])
		application.leave_approver = "test2@example.com"
		self.assertRaises(OverlapError, application.insert)

	def test_global_block_list(self):
		self._clear_roles()

		from frappe.utils.user import add_role
		add_role("test1@example.com", "Employee")
		add_role("test@example.com", "Leave Approver")
		self._add_employee_leave_approver("_T-Employee-0002", "test@example.com")

		application = self.get_application(_test_records[1])
		application.leave_approver = "test@example.com"

		frappe.db.set_value("Leave Block List", "_Test Leave Block List",
			"applies_to_all_departments", 1)
		frappe.db.set_value("Employee", "_T-Employee-0002", "department",
			"_Test Department")

		frappe.set_user("test1@example.com")
		application.insert()

		frappe.set_user("test@example.com")
		application.status = "Approved"
		self.assertRaises(LeaveDayBlockedError, application.submit)

		frappe.db.set_value("Leave Block List", "_Test Leave Block List",
			"applies_to_all_departments", 0)

	def test_leave_approval(self):
		self._clear_roles()

		from frappe.utils.user import add_role
		add_role("test@example.com", "Employee")
		add_role("test1@example.com", "HR User")
		add_role("test1@example.com", "Leave Approver")
		add_role("test2@example.com", "Leave Approver")

		self._test_leave_approval_basic_case()
		self._test_leave_approval_invalid_leave_approver_insert()
		self._test_leave_approval_invalid_leave_approver_submit()
		self._test_leave_approval_valid_leave_approver_insert()

	def _test_leave_approval_basic_case(self):
		self._clear_applications()

		self._add_employee_leave_approver("_T-Employee-0001", "test1@example.com")

		# create leave application as Employee
		frappe.set_user("test@example.com")
		application = self.get_application(_test_records[0])
		application.leave_approver = "test1@example.com"
		application.insert()

		# submit leave application by Leave Approver
		frappe.set_user("test1@example.com")
		application.status = "Approved"
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
		application = self.get_application(_test_records[0])
		application.leave_approver = "test2@example.com"
		application.insert()
		frappe.set_user("test1@example.com")
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
		application = self.get_application(_test_records[0])
		application.leave_approver = "test2@example.com"
		application.insert()

		# change to valid leave approver and try to submit leave application
		frappe.set_user("test2@example.com")
		application.status = "Approved"
		application.submit()
		self.assertEqual(frappe.db.get_value("Leave Application", application.name,
			"docstatus"), 1)

		frappe.db.sql("""delete from `tabEmployee Leave Approver` where parent=%s""",
			"_T-Employee-0001")

		frappe.db.set_value("Employee", "_T-Employee-0001", "department", original_department)
