# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.doctype.shift_request.shift_request import OverlappingShiftRequestError
from erpnext.hr.doctype.shift_type.test_shift_type import setup_shift_type

test_dependencies = ["Shift Type"]


class TestShiftRequest(FrappeTestCase):
	def setUp(self):
		for doctype in ["Shift Request", "Shift Assignment", "Shift Type"]:
			frappe.db.delete(doctype)

	def test_make_shift_request(self):
		"Test creation/updation of Shift Assignment from Shift Request."
		setup_shift_type(shift_type="Day Shift")
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
		setup_shift_type(shift_type="Day Shift")
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

	def test_overlap_for_request_without_to_date(self):
		# shift should be Ongoing if Only from_date is present
		user = "test_shift_request@example.com"
		employee = make_employee(user, company="_Test Company", shift_request_approver=user)
		setup_shift_type(shift_type="Day Shift")

		shift_request = frappe.get_doc(
			{
				"doctype": "Shift Request",
				"shift_type": "Day Shift",
				"company": "_Test Company",
				"employee": employee,
				"from_date": nowdate(),
				"approver": user,
				"status": "Approved",
			}
		).submit()

		shift_request = frappe.get_doc(
			{
				"doctype": "Shift Request",
				"shift_type": "Day Shift",
				"company": "_Test Company",
				"employee": employee,
				"from_date": add_days(nowdate(), 2),
				"approver": user,
				"status": "Approved",
			}
		)

		self.assertRaises(OverlappingShiftRequestError, shift_request.save)

	def test_overlap_for_request_with_from_and_to_dates(self):
		user = "test_shift_request@example.com"
		employee = make_employee(user, company="_Test Company", shift_request_approver=user)
		setup_shift_type(shift_type="Day Shift")

		shift_request = frappe.get_doc(
			{
				"doctype": "Shift Request",
				"shift_type": "Day Shift",
				"company": "_Test Company",
				"employee": employee,
				"from_date": nowdate(),
				"to_date": add_days(nowdate(), 30),
				"approver": user,
				"status": "Approved",
			}
		).submit()

		shift_request = frappe.get_doc(
			{
				"doctype": "Shift Request",
				"shift_type": "Day Shift",
				"company": "_Test Company",
				"employee": employee,
				"from_date": add_days(nowdate(), 10),
				"to_date": add_days(nowdate(), 35),
				"approver": user,
				"status": "Approved",
			}
		)

		self.assertRaises(OverlappingShiftRequestError, shift_request.save)

	def test_overlapping_for_a_fixed_period_shift_and_ongoing_shift(self):
		user = "test_shift_request@example.com"
		employee = make_employee(user, company="_Test Company", shift_request_approver=user)

		# shift setup for 8-12
		shift_type = setup_shift_type(shift_type="Shift 1", start_time="08:00:00", end_time="12:00:00")
		date = nowdate()

		# shift with end date
		frappe.get_doc(
			{
				"doctype": "Shift Request",
				"shift_type": shift_type.name,
				"company": "_Test Company",
				"employee": employee,
				"from_date": date,
				"to_date": add_days(date, 30),
				"approver": user,
				"status": "Approved",
			}
		).submit()

		# shift setup for 11-15
		shift_type = setup_shift_type(shift_type="Shift 2", start_time="11:00:00", end_time="15:00:00")
		shift2 = frappe.get_doc(
			{
				"doctype": "Shift Request",
				"shift_type": shift_type.name,
				"company": "_Test Company",
				"employee": employee,
				"from_date": date,
				"approver": user,
				"status": "Approved",
			}
		)

		self.assertRaises(OverlappingShiftRequestError, shift2.insert)

	def test_allow_non_overlapping_shift_requests_for_same_day(self):
		user = "test_shift_request@example.com"
		employee = make_employee(user, company="_Test Company", shift_request_approver=user)

		# shift setup for 8-12
		shift_type = setup_shift_type(shift_type="Shift 1", start_time="08:00:00", end_time="12:00:00")
		date = nowdate()

		# shift with end date
		frappe.get_doc(
			{
				"doctype": "Shift Request",
				"shift_type": shift_type.name,
				"company": "_Test Company",
				"employee": employee,
				"from_date": date,
				"to_date": add_days(date, 30),
				"approver": user,
				"status": "Approved",
			}
		).submit()

		# shift setup for 13-15
		shift_type = setup_shift_type(shift_type="Shift 2", start_time="13:00:00", end_time="15:00:00")
		frappe.get_doc(
			{
				"doctype": "Shift Request",
				"shift_type": shift_type.name,
				"company": "_Test Company",
				"employee": employee,
				"from_date": date,
				"approver": user,
				"status": "Approved",
			}
		).submit()


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
