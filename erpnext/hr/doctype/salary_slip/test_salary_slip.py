# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import unittest
import frappe
import erpnext
import calendar
from erpnext.accounts.utils import get_fiscal_year
from frappe.utils import getdate, nowdate, add_days, add_months, flt
from erpnext.hr.doctype.salary_structure.salary_structure import make_salary_slip
from erpnext.hr.doctype.process_payroll.test_process_payroll import get_salary_component_account
from erpnext.hr.doctype.process_payroll.process_payroll import get_month_details

class TestSalarySlip(unittest.TestCase):
	def setUp(self):
		make_earning_salary_component(["Basic Salary", "Special Allowance", "HRA"])
		make_deduction_salary_component(["Professional Tax", "TDS"])

		for dt in ["Leave Application", "Leave Allocation", "Salary Slip"]:
			frappe.db.sql("delete from `tab%s`" % dt)

		self.make_holiday_list()

		frappe.db.set_value("Company", erpnext.get_default_company(), "default_holiday_list", "Salary Slip Test Holiday List")

	def tearDown(self):
		frappe.db.set_value("HR Settings", None, "include_holidays_in_total_working_days", 0)
		frappe.set_user("Administrator")

	def test_salary_slip_with_holidays_included(self):
		no_of_days = self.get_no_of_days()
		frappe.db.set_value("HR Settings", None, "include_holidays_in_total_working_days", 1)
		self.make_employee("test_employee@salary.com")
		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "relieving_date", None)
		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "status", "Active")
		ss = frappe.get_doc("Salary Slip",
			self.make_employee_salary_slip("test_employee@salary.com", "Monthly"))

		self.assertEquals(ss.total_working_days, no_of_days[0])
		self.assertEquals(ss.payment_days, no_of_days[0])
		self.assertEquals(ss.earnings[0].amount, 25000)
		self.assertEquals(ss.earnings[1].amount, 3000)
		self.assertEquals(ss.deductions[0].amount, 5000)
		self.assertEquals(ss.deductions[1].amount, 5000)
		self.assertEquals(ss.gross_pay, 40500)
		self.assertEquals(ss.net_pay, 29918)

	def test_salary_slip_with_holidays_excluded(self):
		no_of_days = self.get_no_of_days()
		frappe.db.set_value("HR Settings", None, "include_holidays_in_total_working_days", 0)
		self.make_employee("test_employee@salary.com")
		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "relieving_date", None)
		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "status", "Active")
		ss = frappe.get_doc("Salary Slip",
			self.make_employee_salary_slip("test_employee@salary.com", "Monthly"))

		self.assertEquals(ss.total_working_days, no_of_days[0] - no_of_days[1])
		self.assertEquals(ss.payment_days, no_of_days[0] - no_of_days[1])
		self.assertEquals(ss.earnings[0].amount, 25000)
		self.assertEquals(ss.earnings[0].default_amount, 25000)
		self.assertEquals(ss.earnings[1].amount, 3000)
		self.assertEquals(ss.deductions[0].amount, 5000)
		self.assertEquals(ss.deductions[1].amount, 5000)
		self.assertEquals(ss.gross_pay, 40500)
		self.assertEquals(ss.net_pay, 29918)

	def test_payment_days(self):
		no_of_days = self.get_no_of_days()
		# Holidays not included in working days
		frappe.db.set_value("HR Settings", None, "include_holidays_in_total_working_days", 1)

		# set joinng date in the same month
		self.make_employee("test_employee@salary.com")
		if getdate(nowdate()).day >= 15:
			date_of_joining = getdate(add_days(nowdate(),-10))
			relieving_date = getdate(add_days(nowdate(),-10))
		elif getdate(nowdate()).day < 15 and getdate(nowdate()).day >= 5:
			date_of_joining = getdate(add_days(nowdate(),-3))
			relieving_date = getdate(add_days(nowdate(),-3))
		elif getdate(nowdate()).day < 5 and not getdate(nowdate()).day == 1:
			date_of_joining = getdate(add_days(nowdate(),-1))
			relieving_date = getdate(add_days(nowdate(),-1))
		elif getdate(nowdate()).day == 1:
			date_of_joining = getdate(nowdate())
			relieving_date = getdate(nowdate())

		frappe.db.set_value("Employee", frappe.get_value("Employee",
			{"employee_name":"test_employee@salary.com"}, "name"), "date_of_joining", date_of_joining)
		frappe.db.set_value("Employee", frappe.get_value("Employee",
			{"employee_name":"test_employee@salary.com"}, "name"), "relieving_date", None)
		frappe.db.set_value("Employee", frappe.get_value("Employee",
			{"employee_name":"test_employee@salary.com"}, "name"), "status", "Active")

		ss = frappe.get_doc("Salary Slip",
			self.make_employee_salary_slip("test_employee@salary.com", "Monthly"))

		self.assertEquals(ss.total_working_days, no_of_days[0])
		self.assertEquals(ss.payment_days, (no_of_days[0] - getdate(date_of_joining).day + 1))

		# set relieving date in the same month
		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "date_of_joining", (add_days(nowdate(),-60)))
		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "relieving_date", relieving_date)
		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "status", "Left")
		ss.save()

		self.assertEquals(ss.total_working_days, no_of_days[0])
		self.assertEquals(ss.payment_days, getdate(relieving_date).day)

		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "relieving_date", None)
		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "status", "Active")

	def test_employee_salary_slip_read_permission(self):
		self.make_employee("test_employee@salary.com")

		salary_slip_test_employee = frappe.get_doc("Salary Slip",
			self.make_employee_salary_slip("test_employee@salary.com", "Monthly"))
		frappe.set_user("test_employee@salary.com")
		self.assertTrue(salary_slip_test_employee.has_permission("read"))

	def test_email_salary_slip(self):
		frappe.db.sql("delete from `tabEmail Queue`")

		hr_settings = frappe.get_doc("HR Settings", "HR Settings")
		hr_settings.email_salary_slip_to_employee = 1
		hr_settings.save()

		self.make_employee("test_employee@salary.com")
		ss = frappe.get_doc("Salary Slip",
			self.make_employee_salary_slip("test_employee@salary.com", "Monthly"))
		ss.submit()

		email_queue = frappe.db.sql("""select name from `tabEmail Queue`""")
		self.assertTrue(email_queue)

	def test_loan_repayment_salary_slip(self):
		from erpnext.hr.doctype.employee_loan.test_employee_loan import create_loan_type, create_employee_loan
		employee = self.make_employee("test_employee@salary.com")
		create_loan_type("Car Loan", 500000, 6.4)
		employee_loan = create_employee_loan(employee, "Car Loan", 11000, "Repay Over Number of Periods", 20)
		employee_loan.repay_from_salary = 1
		employee_loan.submit()
		ss = frappe.get_doc("Salary Slip",
			self.make_employee_salary_slip("test_employee@salary.com", "Monthly"))
		ss.submit()
		self.assertEquals(ss.total_loan_repayment, 582)
		self.assertEquals(ss.net_pay, (flt(ss.gross_pay) - (flt(ss.total_deduction) + flt(ss.total_loan_repayment))))

	def test_payroll_frequency(self):
		fiscal_year = get_fiscal_year(nowdate(), company="_Test Company")[0]
		month = "%02d" % getdate(nowdate()).month
		m = get_month_details(fiscal_year, month)

		for payroll_frequncy in ["Monthly", "Bimonthly", "Fortnightly", "Weekly", "Daily"]:
			self.make_employee(payroll_frequncy + "_test_employee@salary.com")
			ss = frappe.get_doc("Salary Slip",
				self.make_employee_salary_slip(payroll_frequncy + "_test_employee@salary.com", payroll_frequncy))
			if payroll_frequncy == "Monthly":
				self.assertEqual(ss.end_date, m['month_end_date'])
			elif payroll_frequncy == "Bimonthly":
				if getdate(ss.start_date).day <= 15:
					self.assertEqual(ss.end_date, m['month_mid_end_date'])
				else:
					self.assertEqual(ss.end_date, m['month_end_date'])
			elif payroll_frequncy == "Fortnightly":
				self.assertEqual(ss.end_date, getdate(add_days(nowdate(),13)))
			elif payroll_frequncy == "Weekly":
				self.assertEqual(ss.end_date, getdate(add_days(nowdate(),6)))
			elif payroll_frequncy == "Daily":
				self.assertEqual(ss.end_date, getdate(nowdate()))

	def make_employee(self, user):
		if not frappe.db.get_value("User", user):
			frappe.get_doc({
				"doctype": "User",
				"email": user,
				"first_name": user,
				"new_password": "password",
				"roles": [{"doctype": "Has Role", "role": "Employee"}]
			}).insert()

		if not frappe.db.get_value("Employee", {"user_id": user}):
			employee = frappe.get_doc({
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
			return employee.name
		else:
			return frappe.get_value("Employee", {"employee_name":user}, "name")

	def make_holiday_list(self):
		fiscal_year = get_fiscal_year(nowdate(), company="_Test Company")
		if not frappe.db.get_value("Holiday List", "Salary Slip Test Holiday List"):
			holiday_list = frappe.get_doc({
				"doctype": "Holiday List",
				"holiday_list_name": "Salary Slip Test Holiday List",
				"from_date": fiscal_year[1],
				"to_date": fiscal_year[2],
				"weekly_off": "Sunday"
			}).insert()
			holiday_list.get_weekly_off_dates()
			holiday_list.save()

	def make_employee_salary_slip(self, user, payroll_frequency):
		employee = frappe.db.get_value("Employee", {"user_id": user})
		salary_structure = make_salary_structure(payroll_frequency + " Salary Structure Test for Salary Slip", payroll_frequency, employee)
		salary_slip = frappe.db.get_value("Salary Slip", {"employee": frappe.db.get_value("Employee", {"user_id": user})})

		if not salary_slip:
			salary_slip = make_salary_slip(salary_structure, employee = employee)
			salary_slip.employee_name = frappe.get_value("Employee", {"name":frappe.db.get_value("Employee", {"user_id": user})}, "employee_name")
			salary_slip.payroll_frequency = payroll_frequency
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

	def get_no_of_days(self):
		no_of_days_in_month = calendar.monthrange(getdate(nowdate()).year,
			getdate(nowdate()).month)
		no_of_holidays_in_month = len([1 for i in calendar.monthcalendar(getdate(nowdate()).year,
			getdate(nowdate()).month) if i[6] != 0])

		return [no_of_days_in_month[1], no_of_holidays_in_month]


def make_earning_salary_component(salary_components):
	for salary_component in salary_components:
		if not frappe.db.exists('Salary Component', salary_component):
			sal_comp = frappe.get_doc({
				"doctype": "Salary Component",
				"salary_component": salary_component,
				"type": "Earning"
			})
			sal_comp.insert()
		get_salary_component_account(salary_component)

def make_deduction_salary_component(salary_components):
	for salary_component in salary_components:
		if not frappe.db.exists('Salary Component', salary_component):
			sal_comp = frappe.get_doc({
				"doctype": "Salary Component",
				"salary_component": salary_component,
				"type": "Deduction"
			})
			sal_comp.insert()
		get_salary_component_account(salary_component)

def make_salary_structure(sal_struct, payroll_frequency, employee):
	if not frappe.db.exists('Salary Structure', sal_struct):
		frappe.get_doc({
			"doctype": "Salary Structure",
			"name": sal_struct,
			"company": erpnext.get_default_company(),
			"employees": get_employee_details(employee),
			"earnings": get_earnings_component(),
			"deductions": get_deductions_component(),
			"payroll_frequency": payroll_frequency,
			"payment_account": frappe.get_value('Account', {'account_type': 'Cash', 'company': erpnext.get_default_company(),'is_group':0}, "name")
		}).insert()

	elif not frappe.db.get_value("Salary Structure Employee",{'parent':sal_struct, 'employee':employee},'name'):
		sal_struct = frappe.get_doc("Salary Structure", sal_struct)
		sal_struct.append("employees", {"employee": employee,
			"employee_name": employee,
			"base": 32000,
			"variable": 3200,
			"from_date": add_months(nowdate(),-1)
			})
		sal_struct.save()
		sal_struct = sal_struct.name
	return sal_struct

def get_employee_details(employee):
	return [{"employee": employee,
			"base": 50000,
			"variable": 5000,
			"from_date": add_months(nowdate(),-1)
			}
		]

def get_earnings_component():
	return [
				{
					"salary_component": 'Basic Salary',
					"abbr":'BS',
					"condition": 'base > 10000',
					"formula": 'base*.5',
					"idx": 1
				},
				{
					"salary_component": 'Basic Salary',
					"abbr":'BS',
					"condition": 'base < 10000',
					"formula": 'base*.2',
					"idx": 2
				},
				{
					"salary_component": 'HRA',
					"abbr":'H',
					"amount": 3000,
					"idx": 3
				},
				{
					"salary_component": 'Special Allowance',
					"abbr":'SA',
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
					"formula": 'base*.1',
					"idx": 1
				},
				{
					"salary_component": 'TDS',
					"abbr":'T',
					"formula": 'base*.1',
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