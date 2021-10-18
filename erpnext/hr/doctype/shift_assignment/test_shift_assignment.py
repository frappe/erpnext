# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe
from frappe.utils import add_days, nowdate

test_dependencies = ["Shift Type"]

class TestShiftAssignment(unittest.TestCase):

	def setUp(self):
		frappe.db.sql("delete from `tabShift Assignment`")

	def test_make_shift_assignment(self):
		shift_assignment = frappe.get_doc({
			"doctype": "Shift Assignment",
			"shift_type": "Day Shift",
			"company": "_Test Company",
			"employee": "_T-Employee-00001",
			"start_date": nowdate()
		}).insert()
		shift_assignment.submit()

		self.assertEqual(shift_assignment.docstatus, 1)

	def test_overlapping_for_ongoing_shift(self):
		# shift should be Ongoing if Only start_date is present and status = Active

		shift_assignment_1 = frappe.get_doc({
			"doctype": "Shift Assignment",
			"shift_type": "Day Shift",
			"company": "_Test Company",
			"employee": "_T-Employee-00001",
			"start_date": nowdate(),
			"status": 'Active'
		}).insert()
		shift_assignment_1.submit()

		self.assertEqual(shift_assignment_1.docstatus, 1)

		shift_assignment = frappe.get_doc({
			"doctype": "Shift Assignment",
			"shift_type": "Day Shift",
			"company": "_Test Company",
			"employee": "_T-Employee-00001",
			"start_date": add_days(nowdate(), 2)
		})

		self.assertRaises(frappe.ValidationError, shift_assignment.save)

	def test_overlapping_for_fixed_period_shift(self):
		# shift should is for Fixed period if Only start_date and end_date both are present and status = Active

			shift_assignment_1 = frappe.get_doc({
				"doctype": "Shift Assignment",
				"shift_type": "Day Shift",
				"company": "_Test Company",
				"employee": "_T-Employee-00001",
				"start_date": nowdate(),
				"end_date": add_days(nowdate(), 30),
				"status": 'Active'
			}).insert()
			shift_assignment_1.submit()


			# it should not allowed within period of any shift.
			shift_assignment_3 = frappe.get_doc({
				"doctype": "Shift Assignment",
				"shift_type": "Day Shift",
				"company": "_Test Company",
				"employee": "_T-Employee-00001",
				"start_date":add_days(nowdate(), 10),
				"end_date": add_days(nowdate(), 35),
				"status": 'Active'
			})

			self.assertRaises(frappe.ValidationError, shift_assignment_3.save)
