# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import nowdate, add_days

class TestShiftRequest(unittest.TestCase):
	def setUp(self):
		for doctype in ["Shift Request", "Shift Assignment"]:
			frappe.db.sql("delete from `tab{doctype}`".format(doctype=doctype))

	def test_make_shift_request(self):
		department = frappe.get_value("Employee", "_T-Employee-00001", 'department')
		set_shift_approver(department)
		approver = frappe.db.sql("""select approver from `tabDepartment Approver` where parent= %s and parentfield = 'shift_request_approver'""", (department))[0][0]

		shift_request = frappe.get_doc({
			"doctype": "Shift Request",
			"shift_type": "Day Shift",
			"company": "_Test Company",
			"employee": "_T-Employee-00001",
			"employee_name": "_Test Employee",
			"from_date": nowdate(),
			"to_date": add_days(nowdate(), 10),
			"approver": approver,
			"status": "Approved"
		})
		shift_request.insert()
		shift_request.submit()
		shift_assignments = frappe.db.sql('''
				SELECT shift_request, employee
				FROM `tabShift Assignment`
				WHERE shift_request = '{0}'
			'''.format(shift_request.name), as_dict=1)
		for d in shift_assignments:
			employee = d.get('employee')
			self.assertEqual(shift_request.employee, employee)
			shift_request.cancel()
			shift_assignment_doc = frappe.get_doc("Shift Assignment", {"shift_request": d.get('shift_request')})
			self.assertEqual(shift_assignment_doc.docstatus, 2)

def set_shift_approver(department):
	department_doc = frappe.get_doc("Department", department)
	department_doc.append('shift_request_approver',{'approver': "test1@example.com"})
	department_doc.save()
	department_doc.reload()