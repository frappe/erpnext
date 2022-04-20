# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate

from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.doctype.shift_assignment.shift_assignment import OverlappingShiftError, get_events
from erpnext.hr.doctype.shift_type.test_shift_type import make_shift_assignment, setup_shift_type

test_dependencies = ["Shift Type"]


class TestShiftAssignment(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Shift Assignment")
		frappe.db.delete("Shift Type")

	def test_make_shift_assignment(self):
		setup_shift_type(shift_type="Day Shift")
		shift_assignment = frappe.get_doc(
			{
				"doctype": "Shift Assignment",
				"shift_type": "Day Shift",
				"company": "_Test Company",
				"employee": "_T-Employee-00001",
				"start_date": nowdate(),
			}
		).insert()
		shift_assignment.submit()

		self.assertEqual(shift_assignment.docstatus, 1)

	def test_overlapping_for_ongoing_shift(self):
		# shift should be Ongoing if Only start_date is present and status = Active
		setup_shift_type(shift_type="Day Shift")
		shift_assignment_1 = frappe.get_doc(
			{
				"doctype": "Shift Assignment",
				"shift_type": "Day Shift",
				"company": "_Test Company",
				"employee": "_T-Employee-00001",
				"start_date": nowdate(),
				"status": "Active",
			}
		).insert()
		shift_assignment_1.submit()

		self.assertEqual(shift_assignment_1.docstatus, 1)

		shift_assignment = frappe.get_doc(
			{
				"doctype": "Shift Assignment",
				"shift_type": "Day Shift",
				"company": "_Test Company",
				"employee": "_T-Employee-00001",
				"start_date": add_days(nowdate(), 2),
			}
		)

		self.assertRaises(OverlappingShiftError, shift_assignment.save)

	def test_overlapping_for_fixed_period_shift(self):
		# shift should is for Fixed period if Only start_date and end_date both are present and status = Active
		setup_shift_type(shift_type="Day Shift")
		shift_assignment_1 = frappe.get_doc(
			{
				"doctype": "Shift Assignment",
				"shift_type": "Day Shift",
				"company": "_Test Company",
				"employee": "_T-Employee-00001",
				"start_date": nowdate(),
				"end_date": add_days(nowdate(), 30),
				"status": "Active",
			}
		).insert()
		shift_assignment_1.submit()

		# it should not allowed within period of any shift.
		shift_assignment_3 = frappe.get_doc(
			{
				"doctype": "Shift Assignment",
				"shift_type": "Day Shift",
				"company": "_Test Company",
				"employee": "_T-Employee-00001",
				"start_date": add_days(nowdate(), 10),
				"end_date": add_days(nowdate(), 35),
				"status": "Active",
			}
		)

		self.assertRaises(OverlappingShiftError, shift_assignment_3.save)

	def test_overlapping_for_a_fixed_period_shift_and_ongoing_shift(self):
		employee = make_employee("test_shift_assignment@example.com", company="_Test Company")

		# shift setup for 8-12
		shift_type = setup_shift_type(shift_type="Shift 1", start_time="08:00:00", end_time="12:00:00")
		date = getdate()
		# shift with end date
		make_shift_assignment(shift_type.name, employee, date, add_days(date, 30))

		# shift setup for 11-15
		shift_type = setup_shift_type(shift_type="Shift 2", start_time="11:00:00", end_time="15:00:00")
		date = getdate()

		# shift assignment without end date
		shift2 = frappe.get_doc(
			{
				"doctype": "Shift Assignment",
				"shift_type": shift_type.name,
				"company": "_Test Company",
				"employee": employee,
				"start_date": date,
			}
		)
		self.assertRaises(OverlappingShiftError, shift2.insert)

	def test_overlap_validation_for_shifts_on_same_day_with_overlapping_timeslots(self):
		employee = make_employee("test_shift_assignment@example.com", company="_Test Company")

		# shift setup for 8-12
		shift_type = setup_shift_type(shift_type="Shift 1", start_time="08:00:00", end_time="12:00:00")
		date = getdate()
		make_shift_assignment(shift_type.name, employee, date)

		# shift setup for 11-15
		shift_type = setup_shift_type(shift_type="Shift 2", start_time="11:00:00", end_time="15:00:00")
		date = getdate()

		shift2 = frappe.get_doc(
			{
				"doctype": "Shift Assignment",
				"shift_type": shift_type.name,
				"company": "_Test Company",
				"employee": employee,
				"start_date": date,
			}
		)
		self.assertRaises(OverlappingShiftError, shift2.insert)

	def test_multiple_shift_assignments_for_same_day(self):
		employee = make_employee("test_shift_assignment@example.com", company="_Test Company")

		# shift setup for 8-12
		shift_type = setup_shift_type(shift_type="Shift 1", start_time="08:00:00", end_time="12:00:00")
		date = getdate()
		make_shift_assignment(shift_type.name, employee, date)

		# shift setup for 13-15
		shift_type = setup_shift_type(shift_type="Shift 2", start_time="13:00:00", end_time="15:00:00")
		date = getdate()
		make_shift_assignment(shift_type.name, employee, date)

	def test_shift_assignment_calendar(self):
		employee1 = make_employee("test_shift_assignment1@example.com", company="_Test Company")
		employee2 = make_employee("test_shift_assignment2@example.com", company="_Test Company")

		shift_type = setup_shift_type(shift_type="Shift 1", start_time="08:00:00", end_time="12:00:00")
		date = getdate()
		shift1 = make_shift_assignment(shift_type.name, employee1, date)
		make_shift_assignment(shift_type.name, employee2, date)

		events = get_events(
			start=date, end=date, filters=[["Shift Assignment", "employee", "=", employee1, False]]
		)
		self.assertEqual(len(events), 1)
		self.assertEqual(events[0]["name"], shift1.name)
