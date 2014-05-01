# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
import unittest

class TestSalarySlip(unittest.TestCase):
	def setUp(self):
		frappe.db.sql("""delete from `tabLeave Application`""")
		frappe.db.sql("""delete from `tabSalary Slip`""")
		from erpnext.hr.doctype.leave_application.test_leave_application import _test_records as leave_applications
		la = frappe.copy_doc(leave_applications[2])
		la.insert()
		la.status = "Approved"
		la.submit()

	def tearDown(self):
		frappe.db.set_value("HR Settings", "HR Settings", "include_holidays_in_total_working_days", 0)

	def test_salary_slip_with_holidays_included(self):
		frappe.db.set_value("HR Settings", "HR Settings", "include_holidays_in_total_working_days", 1)
		ss = frappe.copy_doc(test_records[0])
		ss.insert()
		self.assertEquals(ss.total_days_in_month, 31)
		self.assertEquals(ss.payment_days, 30)
		self.assertEquals(ss.earning_details[0].e_modified_amount, 14516.13)
		self.assertEquals(ss.earning_details[1].e_modified_amount, 500)
		self.assertEquals(ss.deduction_details[0].d_modified_amount, 100)
		self.assertEquals(ss.deduction_details[1].d_modified_amount, 48.39)
		self.assertEquals(ss.gross_pay, 15016.13)
		self.assertEquals(ss.net_pay, 14867.74)

	def test_salary_slip_with_holidays_excluded(self):
		ss = frappe.copy_doc(test_records[0])
		ss.insert()
		self.assertEquals(ss.total_days_in_month, 30)
		self.assertEquals(ss.payment_days, 29)
		self.assertEquals(ss.earning_details[0].e_modified_amount, 14500)
		self.assertEquals(ss.earning_details[1].e_modified_amount, 500)
		self.assertEquals(ss.deduction_details[0].d_modified_amount, 100)
		self.assertEquals(ss.deduction_details[1].d_modified_amount, 48.33)
		self.assertEquals(ss.gross_pay, 15000)
		self.assertEquals(ss.net_pay, 14851.67)

test_dependencies = ["Leave Application"]

test_records = frappe.get_test_records('Salary Slip')
