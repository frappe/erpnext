# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import nowdate

class TestShiftRequest(unittest.TestCase):
	def test_make_shift_request(self):
		shift_request = frappe.get_doc({
			"doctype": "Shift Request",
			"shift_type": "Day Shift",
			"company": "_Test Company",
			"employee": "_T-Employee-00001",
			"employee_name": "_Test Employee",
			"start_date": nowdate(),
			"end_date": nowdate()
		})
		shift_request.insert()
		shift_request.submit()
		shift_assignment = frappe.db.sql("""select employee
											from `tabShift Assignment`
											where shift_request = %s""", shift_request.name)
		if shift_assignment:
			employee = shift_assignment[0][0]
		self.assertEqual(shift_request.employee, employee)