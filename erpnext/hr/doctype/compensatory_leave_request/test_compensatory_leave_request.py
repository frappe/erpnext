# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import add_days, add_months, today

from erpnext.hr.doctype.attendance_request.test_attendance_request import get_employee
from erpnext.hr.doctype.leave_application.leave_application import get_leave_balance_on
from erpnext.hr.doctype.leave_period.test_leave_period import create_leave_period

test_dependencies = ["Employee"]


class TestCompensatoryLeaveRequest(unittest.TestCase):
	def setUp(self):
		frappe.db.sql(""" delete from `tabCompensatory Leave Request`""")
		frappe.db.sql(""" delete from `tabLeave Ledger Entry`""")
		frappe.db.sql(""" delete from `tabLeave Allocation`""")
		frappe.db.sql(
			""" delete from `tabAttendance` where attendance_date in {0} """.format(
				(today(), add_days(today(), -1))
			)
		)  # nosec
		create_leave_period(add_months(today(), -3), add_months(today(), 3), "_Test Company")
		create_holiday_list()

		employee = get_employee()
		employee.holiday_list = "_Test Compensatory Leave"
		employee.save()

	def test_leave_balance_on_submit(self):
		"""check creation of leave allocation on submission of compensatory leave request"""
		employee = get_employee()
		mark_attendance(employee)
		compensatory_leave_request = get_compensatory_leave_request(employee.name)

		before = get_leave_balance_on(employee.name, compensatory_leave_request.leave_type, today())
		compensatory_leave_request.submit()

		self.assertEqual(
			get_leave_balance_on(
				employee.name, compensatory_leave_request.leave_type, add_days(today(), 1)
			),
			before + 1,
		)

	def test_leave_allocation_update_on_submit(self):
		employee = get_employee()
		mark_attendance(employee, date=add_days(today(), -1))
		compensatory_leave_request = get_compensatory_leave_request(
			employee.name, leave_date=add_days(today(), -1)
		)
		compensatory_leave_request.submit()

		# leave allocation creation on submit
		leaves_allocated = frappe.db.get_value(
			"Leave Allocation",
			{"name": compensatory_leave_request.leave_allocation},
			["total_leaves_allocated"],
		)
		self.assertEqual(leaves_allocated, 1)

		mark_attendance(employee)
		compensatory_leave_request = get_compensatory_leave_request(employee.name)
		compensatory_leave_request.submit()

		# leave allocation updates on submission of second compensatory leave request
		leaves_allocated = frappe.db.get_value(
			"Leave Allocation",
			{"name": compensatory_leave_request.leave_allocation},
			["total_leaves_allocated"],
		)
		self.assertEqual(leaves_allocated, 2)

	def test_creation_of_leave_ledger_entry_on_submit(self):
		"""check creation of leave ledger entry on submission of leave request"""
		employee = get_employee()
		mark_attendance(employee)
		compensatory_leave_request = get_compensatory_leave_request(employee.name)
		compensatory_leave_request.submit()

		filters = dict(transaction_name=compensatory_leave_request.leave_allocation)
		leave_ledger_entry = frappe.get_all("Leave Ledger Entry", fields="*", filters=filters)

		self.assertEqual(len(leave_ledger_entry), 1)
		self.assertEqual(leave_ledger_entry[0].employee, compensatory_leave_request.employee)
		self.assertEqual(leave_ledger_entry[0].leave_type, compensatory_leave_request.leave_type)
		self.assertEqual(leave_ledger_entry[0].leaves, 1)

		# check reverse leave ledger entry on cancellation
		compensatory_leave_request.cancel()
		leave_ledger_entry = frappe.get_all(
			"Leave Ledger Entry", fields="*", filters=filters, order_by="creation desc"
		)

		self.assertEqual(len(leave_ledger_entry), 2)
		self.assertEqual(leave_ledger_entry[0].employee, compensatory_leave_request.employee)
		self.assertEqual(leave_ledger_entry[0].leave_type, compensatory_leave_request.leave_type)
		self.assertEqual(leave_ledger_entry[0].leaves, -1)


def get_compensatory_leave_request(employee, leave_date=today()):
	prev_comp_leave_req = frappe.db.get_value(
		"Compensatory Leave Request",
		dict(
			leave_type="Compensatory Off",
			work_from_date=leave_date,
			work_end_date=leave_date,
			employee=employee,
		),
		"name",
	)
	if prev_comp_leave_req:
		return frappe.get_doc("Compensatory Leave Request", prev_comp_leave_req)

	return frappe.get_doc(
		dict(
			doctype="Compensatory Leave Request",
			employee=employee,
			leave_type="Compensatory Off",
			work_from_date=leave_date,
			work_end_date=leave_date,
			reason="test",
		)
	).insert()


def mark_attendance(employee, date=today(), status="Present"):
	if not frappe.db.exists(
		dict(doctype="Attendance", employee=employee.name, attendance_date=date, status="Present")
	):
		attendance = frappe.get_doc(
			{"doctype": "Attendance", "employee": employee.name, "attendance_date": date, "status": status}
		)
		attendance.save()
		attendance.submit()


def create_holiday_list():
	if frappe.db.exists("Holiday List", "_Test Compensatory Leave"):
		return

	holiday_list = frappe.get_doc(
		{
			"doctype": "Holiday List",
			"from_date": add_months(today(), -3),
			"to_date": add_months(today(), 3),
			"holidays": [
				{"description": "Test Holiday", "holiday_date": today()},
				{"description": "Test Holiday 1", "holiday_date": add_days(today(), -1)},
			],
			"holiday_list_name": "_Test Compensatory Leave",
		}
	)
	holiday_list.save()
