# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import unittest
import frappe
import erpnext
from frappe.utils.make_random import get_random
from frappe.utils import today, now_datetime, getdate, cstr, add_years, nowdate
from erpnext.hr.doctype.salary_structure.salary_structure import make_salary_slip
from erpnext.hr.doctype.process_payroll.test_process_payroll import get_salary_component_account

class TestSalarySlip(unittest.TestCase):
	def setUp(self):
		make_salary_component(["Basic Salary", "Allowance", "HRA", "Professional Tax", "TDS"])
		
		for dt in ["Leave Application", "Leave Allocation", "Salary Slip"]:
			frappe.db.sql("delete from `tab%s`" % dt)

		self.make_holiday_list()
		frappe.db.set_value("Company", erpnext.get_default_company(), "default_holiday_list", "Salary Slip Test Holiday List")

		from erpnext.hr.doctype.leave_application.test_leave_application import _test_records as leave_applications
		la = frappe.copy_doc(leave_applications[2])
		la.insert()
		la.status = "Approved"
		la.submit()

	def tearDown(self):
		frappe.db.set_value("HR Settings", None, "include_holidays_in_total_working_days", 0)
		frappe.set_user("Administrator")

	def test_salary_slip_with_holidays_included(self):
		frappe.db.set_value("HR Settings", None, "include_holidays_in_total_working_days", 1)
		self.make_employee("test_employee@salary.com")
		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "relieving_date", None)
		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "status", "Active")
		ss = frappe.get_doc("Salary Slip",
			self.make_employee_salary_slip("test_employee@salary.com"))

		self.assertEquals(ss.total_days_in_month, 31)
		self.assertEquals(ss.payment_days, 31)
		self.assertEquals(ss.earnings[0].amount, 5000)
		self.assertEquals(ss.earnings[1].amount, 3000)
		self.assertEquals(ss.deductions[0].amount, 5000)
		self.assertEquals(ss.deductions[1].amount, 2500)
		self.assertEquals(ss.gross_pay, 10500)
		self.assertEquals(ss.net_pay, 3000)

	def test_salary_slip_with_holidays_excluded(self):
		frappe.db.set_value("HR Settings", None, "include_holidays_in_total_working_days", 0)
		self.make_employee("test_employee@salary.com")
		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "relieving_date", None)
		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "status", "Active")
		ss = frappe.get_doc("Salary Slip",
			self.make_employee_salary_slip("test_employee@salary.com"))

		self.assertEquals(ss.total_days_in_month, 28)
		self.assertEquals(ss.payment_days, 28)
		self.assertEquals(ss.earnings[0].amount, 5000)
		self.assertEquals(ss.earnings[0].default_amount, 5000)
		self.assertEquals(ss.earnings[1].amount, 3000)
		self.assertEquals(ss.deductions[0].amount, 5000)
		self.assertEquals(ss.deductions[1].amount, 2500)
		self.assertEquals(ss.gross_pay, 10500)
		self.assertEquals(ss.net_pay, 3000)
		
	def test_payment_days(self):
		# Holidays not included in working days
		frappe.db.set_value("HR Settings", None, "include_holidays_in_total_working_days", 0)

		# set joinng date in the same month
		self.make_employee("test_employee@salary.com")
		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "date_of_joining", "2013-01-11")
		
		ss = frappe.get_doc("Salary Slip",
			self.make_employee_salary_slip("test_employee@salary.com"))

		self.assertEquals(ss.total_days_in_month, 28)
		self.assertEquals(ss.payment_days, 28)

		# set relieving date in the same month
		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "relieving_date", "12-12-2016")
		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "status", "Left")
		
		self.assertEquals(ss.total_days_in_month, 28)
		self.assertEquals(ss.payment_days, 28)
		ss.save()
		
		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "relieving_date", None)
		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "status", "Active")
		# Holidays included in working days
		frappe.db.set_value("HR Settings", None, "include_holidays_in_total_working_days", 1)	
		self.assertEquals(ss.total_days_in_month, 28)
		self.assertEquals(ss.payment_days, 28)
		ss.save()
				#
		# frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "date_of_joining", "2001-01-11")
		# frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "relieving_date", None)

	def test_employee_salary_slip_read_permission(self):
		self.make_employee("test_employee@salary.com")

		salary_slip_test_employee = frappe.get_doc("Salary Slip",
			self.make_employee_salary_slip("test_employee@salary.com"))
		frappe.set_user("test_employee@salary.com")
		self.assertTrue(salary_slip_test_employee.has_permission("read"))

	def test_email_salary_slip(self):
		frappe.db.sql("delete from `tabEmail Queue`")

		hr_settings = frappe.get_doc("HR Settings", "HR Settings")
		hr_settings.email_salary_slip_to_employee = 1
		hr_settings.save()

		self.make_employee("test_employee@salary.com")
		ss = frappe.get_doc("Salary Slip",
			self.make_employee_salary_slip("test_employee@salary.com"))
		ss.submit()
		email_queue = frappe.db.sql("""select name from `tabEmail Queue`""")
		self.assertTrue(email_queue)


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
				"naming_series": "EMP-",
				"employee_name": user,
				"company": erpnext.get_default_company(),
				"user_id": user,
				"date_of_birth": "1990-05-08",
				"date_of_joining": "2013-01-01",
				"department": frappe.get_all("Department", fields="name")[0].name,
				"gender": "Female",
				"company_email": user,
				"prefered_contact_email": "Company Email",
				"prefered_email": user,
				"status": "Active",
				"employment_type": "Intern"
			}).insert()
			
	def make_holiday_list(self):
		if not frappe.db.get_value("Holiday List", "Salary Slip Test Holiday List"):
			holiday_list = frappe.get_doc({
				"doctype": "Holiday List",
				"holiday_list_name": "Salary Slip Test Holiday List",
				"from_date": nowdate(),
				"to_date": add_years(nowdate(), 1),
				"weekly_off": "Sunday"
			}).insert()	
			holiday_list.get_weekly_off_dates()
			holiday_list.save()
				
	def make_employee_salary_slip(self, user):
		employee = frappe.db.get_value("Employee", {"user_id": user})
		salary_structure = make_salary_structure("Salary Structure Test for Salary Slip")
		salary_slip = frappe.db.get_value("Salary Slip", {"employee": frappe.db.get_value("Employee", {"user_id": user})})
		
		if not salary_slip:
			salary_slip = make_salary_slip(salary_structure, employee = employee)
			salary_slip.employee_name = frappe.get_value("Employee", {"name":frappe.db.get_value("Employee", {"user_id": user})}, "employee_name")
			salary_slip.month = "12"
			salary_slip.fiscal_year = "_Test Fiscal Year 2016"
			salary_slip.posting_date = nowdate()
			salary_slip.insert()
			# salary_slip.submit()
			salary_slip = salary_slip.name

		return salary_slip

	def make_activity_for_employee(self):
		activity_type = frappe.get_doc("Activity Type", "_Test Activity Type")
		activity_type.billing_rate = 50
		activity_type.costing_rate = 20
		activity_type.wage_rate = 25
		activity_type.save()

def make_salary_component(salary_components):
	for salary_component in salary_components:
		if not frappe.db.exists('Salary Component', salary_component):
			sal_comp = frappe.get_doc({
				"doctype": "Salary Component",
				"salary_component": salary_component
			})
			sal_comp.insert()
		get_salary_component_account(salary_component)

def make_salary_structure(sal_struct):
	if not frappe.db.exists('Salary Structure', sal_struct):
		frappe.get_doc({
			"doctype": "Salary Structure",
			"name": sal_struct,
			"company": erpnext.get_default_company(),
			"from_date": nowdate(),
			"employees": get_employee_details(),
			"earnings": get_earnings_component(),
			"deductions": get_deductions_component(),
			"payment_account": frappe.get_value('Account', {'account_type': 'Cash', 'company': erpnext.get_default_company(),'is_group':0}, "name")
		}).insert()
	return sal_struct
			
			
def get_employee_details():
	return [{"employee": frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"),
			"base": 25000,
			"variable": 5000
			}
		]
			
def get_earnings_component():	
	return [
				{
					"salary_component": 'Basic Salary',
					"abbr":'BS',
					"condition": 'base > 10000',
					"formula": 'base*.2',
					"idx": 1
				},
				{
					"salary_component": 'Basic Salary',
					"abbr":'BS',
					"condition": 'base < 10000',
					"formula": 'base*.1',
					"idx": 2
				},
				{
					"salary_component": 'HRA',
					"abbr":'H',
					"amount": 3000,
					"idx": 3
				},
				{
					"salary_component": 'Allowance',
					"abbr":'A',
					"condition": 'H < 10000',
					"formula": 'BS*.5',
					"idx": 4
				},
			]
			
def get_deductions_component():	
	return [
				{
					"salary_component": 'Professional Tax',
					"abbr":'PT',
					"condition": 'base > 10000',
					"formula": 'base*.2',
					"idx": 1
				},
				{
					"salary_component": 'TDS',
					"abbr":'T',
					"formula": 'base*.5',
					"idx": 2
				},
				{
					"salary_component": 'TDS',
					"abbr":'T',
					"condition": 'employment_type=="Intern"',
					"formula": 'base*.1',
					"idx": 3
				}
			]			

test_dependencies = ["Leave Application", "Holiday List"]
			