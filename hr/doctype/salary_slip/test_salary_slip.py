# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes
import unittest

class TestSalarySlip(unittest.TestCase):
	def setUp(self):
		webnotes.conn.sql("""delete from `tabLeave Application`""")
		webnotes.conn.sql("""delete from `tabSalary Slip`""")
		from hr.doctype.leave_application.test_leave_application import test_records as leave_applications
		la = webnotes.bean(copy=leave_applications[4])
		la.insert()
		la.doc.status = "Approved"
		la.submit()
		
	def tearDown(self):
		webnotes.conn.set_value("HR Settings", "HR Settings", "include_holidays_in_total_working_days", 0)
		
	def test_salary_slip_with_holidays_included(self):
		webnotes.conn.set_value("HR Settings", "HR Settings", "include_holidays_in_total_working_days", 1)
		ss = webnotes.bean(copy=test_records[0])
		ss.insert()
		self.assertEquals(ss.doc.total_days_in_month, 31)
		self.assertEquals(ss.doc.payment_days, 30)
		self.assertEquals(ss.doclist[1].e_modified_amount, 14516.13)
		self.assertEquals(ss.doclist[2].e_modified_amount, 500)
		self.assertEquals(ss.doclist[3].d_modified_amount, 100)
		self.assertEquals(ss.doclist[4].d_modified_amount, 48.39)
		self.assertEquals(ss.doc.gross_pay, 15016.13)
		self.assertEquals(ss.doc.net_pay, 14867.74)
		
	def test_salary_slip_with_holidays_excluded(self):
		ss = webnotes.bean(copy=test_records[0])
		ss.insert()
		self.assertEquals(ss.doc.total_days_in_month, 30)
		self.assertEquals(ss.doc.payment_days, 29)
		self.assertEquals(ss.doclist[1].e_modified_amount, 14500)
		self.assertEquals(ss.doclist[2].e_modified_amount, 500)
		self.assertEquals(ss.doclist[3].d_modified_amount, 100)
		self.assertEquals(ss.doclist[4].d_modified_amount, 48.33)
		self.assertEquals(ss.doc.gross_pay, 15000)
		self.assertEquals(ss.doc.net_pay, 14851.67)

test_dependencies = ["Leave Application"]

test_records = [
	[
		{
			"doctype": "Salary Slip",
			"employee": "_T-Employee-0001",
			"employee_name": "_Test Employee",
			"company": "_Test Company",
			"fiscal_year": "_Test Fiscal Year 2013",
			"month": "01",
			"total_days_in_month": 31,
			"payment_days": 31
		},
		{
			"doctype": "Salary Slip Earning",
			"parentfield": "earning_details",
			"e_type": "_Test Basic Salary",
			"e_amount": 15000,
			"e_depends_on_lwp": 1
		},
		{
			"doctype": "Salary Slip Earning",
			"parentfield": "earning_details",
			"e_type": "_Test Allowance",
			"e_amount": 500,
			"e_depends_on_lwp": 0
		},
		{
			"doctype": "Salary Slip Deduction",
			"parentfield": "deduction_details",
			"d_type": "_Test Professional Tax",
			"d_amount": 100,
			"d_depends_on_lwp": 0
		},
		{
			"doctype": "Salary Slip Deduction",
			"parentfield": "deduction_details",
			"d_type": "_Test TDS",
			"d_amount": 50,
			"d_depends_on_lwp": 1
		},
	]
]