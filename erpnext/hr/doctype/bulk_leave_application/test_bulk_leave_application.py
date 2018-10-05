# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import nowdate, add_days
from erpnext.hr.doctype.employee.test_employee import make_employee

class TestBulkLeaveApplication(unittest.TestCase):
	def setUp(self):
		frappe.db.sql("delete from `tabLeave Application`")
		if not frappe.db.exists("Leave Type", "_Test Leave Type Negative"):
			frappe.get_doc({
				"doctype": "Leave Type",
				"leave_type_name": "_Test Leave Type Negative",
				"allow_negative": 1,
				"include_holiday": 1
			}).insert()

 	def test_bulk_leave_application(self):
		leave_type = "_Test Leave Type Negative"
		employee = make_employee("test_email@erpnext.org")

		bla = frappe.new_doc("Bulk Leave Application")
		bla.employee = employee
		bla.append("periods", {
		"leave_type": leave_type,
		"from_date": nowdate(),
		"to_date": add_days(nowdate(), 1)
		})
		bla.create_leave_applications()

		leaves = frappe.db.sql("""select total_leave_days from `tabLeave Application`
			where employee=%s and leave_type=%s and docstatus=1""", (employee, leave_type))[0][0]
		self.assertEqual(leaves, 2)
