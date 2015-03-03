# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import unittest
import frappe
from frappe.utils import today
from erpnext.hr.doctype.employee.employee import make_salary_structure
from erpnext.hr.doctype.salary_structure.salary_structure import make_salary_slip

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
		frappe.set_user("Administrator")

	def test_salary_slip_with_holidays_included(self):
		frappe.db.set_value("HR Settings", "HR Settings", "include_holidays_in_total_working_days", 1)
		ss = frappe.copy_doc(test_records[0])
		ss.insert()
		self.assertEquals(ss.total_days_in_month, 31)
		self.assertEquals(ss.payment_days, 30)
		self.assertEquals(ss.earnings[0].e_modified_amount, 14516.13)
		self.assertEquals(ss.earnings[1].e_modified_amount, 500)
		self.assertEquals(ss.deductions[0].d_modified_amount, 100)
		self.assertEquals(ss.deductions[1].d_modified_amount, 48.39)
		self.assertEquals(ss.gross_pay, 15016.13)
		self.assertEquals(ss.net_pay, 14867.74)

	def test_salary_slip_with_holidays_excluded(self):
		ss = frappe.copy_doc(test_records[0])
		ss.insert()
		self.assertEquals(ss.total_days_in_month, 30)
		self.assertEquals(ss.payment_days, 29)
		self.assertEquals(ss.earnings[0].e_modified_amount, 14500)
		self.assertEquals(ss.earnings[1].e_modified_amount, 500)
		self.assertEquals(ss.deductions[0].d_modified_amount, 100)
		self.assertEquals(ss.deductions[1].d_modified_amount, 48.33)
		self.assertEquals(ss.gross_pay, 15000)
		self.assertEquals(ss.net_pay, 14851.67)

	def test_employee_salary_slip_read_permission(self):
		self.make_employee("test_employee@example.com")
		self.make_employee("test_employee_2@example.com")

		salary_slip_test_employee = frappe.get_doc("Salary Slip",
			self.make_employee_salary_slip("test_employee@example.com"))

		salary_slip_test_employee_2 = frappe.get_doc("Salary Slip",
			self.make_employee_salary_slip("test_employee_2@example.com"))

		frappe.set_user("test_employee@example.com")
		self.assertTrue(salary_slip_test_employee.has_permission("read"))

	def make_employee(self, user):
		if not frappe.db.get_value("User", user):
			frappe.get_doc({
				"doctype": "User",
				"email": user,
				"first_name": user,
				"new_password": "password",
				"user_roles": [{"doctype": "UserRole", "role": "Employee"}]
			}).insert()

		if not frappe.db.get_value("Employee", {"user_id": user}):
			frappe.get_doc({
				"doctype": "Employee",
				"naming_series": "_T-Employee-",
				"employee_name": user,
				"user_id": user,
				"company": "_Test Company",
				"date_of_birth": "1990-05-08",
				"date_of_joining": "2013-01-01",
				"department": "_Test Department 1",
				"gender": "Female",
				"status": "Active"
			}).insert()

	def make_employee_salary_slip(self, user):
		employee = frappe.db.get_value("Employee", {"user_id": user})
		salary_structure = frappe.db.get_value("Salary Structure", {"employee": employee})
		if not salary_structure:
			salary_structure = make_salary_structure(employee)
			salary_structure.from_date = today()
			salary_structure.insert()
			salary_structure = salary_structure.name

		salary_slip = frappe.db.get_value("Salary Slip", {"employee": employee})
		if not salary_slip:
			salary_slip = make_salary_slip(salary_structure)
			salary_slip.insert()
			salary_slip.submit()
			salary_slip = salary_slip.name

		return salary_slip

test_dependencies = ["Leave Application"]

test_records = frappe.get_test_records('Salary Slip')
