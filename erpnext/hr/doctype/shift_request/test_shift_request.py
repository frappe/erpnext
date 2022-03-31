# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import add_days, nowdate

from erpnext.hr.doctype.employee.test_employee import make_employee

test_dependencies = ["Shift Type"]


class TestShiftRequest(unittest.TestCase):
	def setUp(self):
		for doctype in ["Shift Request", "Shift Assignment"]:
			frappe.db.sql("delete from `tab{doctype}`".format(doctype=doctype))

	def tearDown(self):
		frappe.db.rollback()

	def test_make_shift_request(self):
		"Test creation/updation of Shift Assignment from Shift Request."
		department = frappe.get_value("Employee", "_T-Employee-00001", "department")
		set_shift_approver(department)
		approver = frappe.db.sql(
			"""select approver from `tabDepartment Approver` where parent= %s and parentfield = 'shift_request_approver'""",
			(department),
		)[0][0]

		shift_request = make_shift_request(approver)

		# Only one shift assignment is created against a shift request
		shift_assignment = frappe.db.get_value(
			"Shift Assignment",
			filters={"shift_request": shift_request.name},
			fieldname=["employee", "docstatus"],
			as_dict=True,
		)
		self.assertEqual(shift_request.employee, shift_assignment.employee)
		self.assertEqual(shift_assignment.docstatus, 1)

		shift_request.cancel()

		shift_assignment_docstatus = frappe.db.get_value(
			"Shift Assignment", filters={"shift_request": shift_request.name}, fieldname="docstatus"
		)
		self.assertEqual(shift_assignment_docstatus, 2)

	def test_shift_request_approver_perms(self):
		employee = frappe.get_doc("Employee", "_T-Employee-00001")
		user = "test_approver_perm_emp@example.com"
		make_employee(user, "_Test Company")

		# set approver for employee
		employee.reload()
		employee.shift_request_approver = user
		employee.save()

		shift_request = make_shift_request(user, do_not_submit=True)
		self.assertTrue(shift_request.name in frappe.share.get_shared("Shift Request", user))

		# check shared doc revoked
		shift_request.reload()
		department = frappe.get_value("Employee", "_T-Employee-00001", "department")
		set_shift_approver(department)
		department_approver = frappe.db.sql(
			"""select approver from `tabDepartment Approver` where parent= %s and parentfield = 'shift_request_approver'""",
			(department),
		)[0][0]
		shift_request.approver = department_approver
		shift_request.save()
		self.assertTrue(shift_request.name not in frappe.share.get_shared("Shift Request", user))

		shift_request.reload()
		shift_request.approver = user
		shift_request.save()

		frappe.set_user(user)
		shift_request.reload()
		shift_request.status = "Approved"
		shift_request.submit()

		# unset approver
		frappe.set_user("Administrator")
		employee.reload()
		employee.shift_request_approver = ""
		employee.save()


def set_shift_approver(department):
	department_doc = frappe.get_doc("Department", department)
	department_doc.append("shift_request_approver", {"approver": "test1@example.com"})
	department_doc.save()
	department_doc.reload()


def make_shift_request(approver, do_not_submit=0):
	shift_request = frappe.get_doc(
		{
			"doctype": "Shift Request",
			"shift_type": "Day Shift",
			"company": "_Test Company",
			"employee": "_T-Employee-00001",
			"employee_name": "_Test Employee",
			"from_date": nowdate(),
			"to_date": add_days(nowdate(), 10),
			"approver": approver,
			"status": "Approved",
		}
	).insert()

	if do_not_submit:
		return shift_request

	shift_request.submit()
	return shift_request
