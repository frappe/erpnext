# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import unittest
import frappe
import erpnext
import calendar
from erpnext.accounts.utils import get_fiscal_year
from frappe.utils.make_random import get_random
from frappe.utils import getdate, nowdate, add_days, add_months, flt
from erpnext.hr.doctype.salary_structure.salary_structure import make_salary_slip
from erpnext.hr.doctype.payroll_entry.payroll_entry import get_month_details
from erpnext.hr.doctype.employee.test_employee import make_employee


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
		make_employee("test_employee@salary.com")
		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "relieving_date", None)
		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "status", "Active")
		ss = make_employee_salary_slip("test_employee@salary.com", "Monthly")

		self.assertEqual(ss.total_working_days, no_of_days[0])
		self.assertEqual(ss.payment_days, no_of_days[0])
		self.assertEqual(ss.earnings[0].amount, 25000)
		self.assertEqual(ss.earnings[1].amount, 3000)
		self.assertEqual(ss.deductions[0].amount, 5000)
		self.assertEqual(ss.deductions[1].amount, 5000)
		self.assertEqual(ss.gross_pay, 40500)
		self.assertEqual(ss.net_pay, 29918)

	def test_salary_slip_with_holidays_excluded(self):
		no_of_days = self.get_no_of_days()
		frappe.db.set_value("HR Settings", None, "include_holidays_in_total_working_days", 0)
		make_employee("test_employee@salary.com")
		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "relieving_date", None)
		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "status", "Active")
		ss = make_employee_salary_slip("test_employee@salary.com", "Monthly")

		self.assertEqual(ss.total_working_days, no_of_days[0] - no_of_days[1])
		self.assertEqual(ss.payment_days, no_of_days[0] - no_of_days[1])
		self.assertEqual(ss.earnings[0].amount, 25000)
		self.assertEqual(ss.earnings[0].default_amount, 25000)
		self.assertEqual(ss.earnings[1].amount, 3000)
		self.assertEqual(ss.deductions[0].amount, 5000)
		self.assertEqual(ss.deductions[1].amount, 5000)
		self.assertEqual(ss.gross_pay, 40500)
		self.assertEqual(ss.net_pay, 29918)

	def test_payment_days(self):
		no_of_days = self.get_no_of_days()
		# Holidays not included in working days
		frappe.db.set_value("HR Settings", None, "include_holidays_in_total_working_days", 1)

		# set joinng date in the same month
		make_employee("test_employee@salary.com")
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

		ss = make_employee_salary_slip("test_employee@salary.com", "Monthly")

		self.assertEqual(ss.total_working_days, no_of_days[0])
		self.assertEqual(ss.payment_days, (no_of_days[0] - getdate(date_of_joining).day + 1))

		# set relieving date in the same month
		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "date_of_joining", (add_days(nowdate(),-60)))
		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "relieving_date", relieving_date)
		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "status", "Left")
		ss.save()

		self.assertEqual(ss.total_working_days, no_of_days[0])
		self.assertEqual(ss.payment_days, getdate(relieving_date).day)

		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "relieving_date", None)
		frappe.db.set_value("Employee", frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"), "status", "Active")

	def test_employee_salary_slip_read_permission(self):
		make_employee("test_employee@salary.com")

		salary_slip_test_employee = make_employee_salary_slip("test_employee@salary.com", "Monthly")
		frappe.set_user("test_employee@salary.com")
		self.assertTrue(salary_slip_test_employee.has_permission("read"))

	def test_email_salary_slip(self):
		frappe.db.sql("delete from `tabEmail Queue`")

		hr_settings = frappe.get_doc("HR Settings", "HR Settings")
		hr_settings.email_salary_slip_to_employee = 1
		hr_settings.save()

		make_employee("test_employee@salary.com")
		ss = make_employee_salary_slip("test_employee@salary.com", "Monthly")
		ss.submit()

		email_queue = frappe.db.sql("""select name from `tabEmail Queue`""")
		self.assertTrue(email_queue)

	def test_loan_repayment_salary_slip(self):
		from erpnext.hr.doctype.loan.test_loan import create_loan_type, create_loan
		applicant = make_employee("test_employee@salary.com")
		create_loan_type("Car Loan", 500000, 6.4)
		loan = create_loan(applicant, "Car Loan", 11000, "Repay Over Number of Periods", 20)
		loan.repay_from_salary = 1
		loan.submit()
		ss = make_employee_salary_slip("test_employee@salary.com", "Monthly")
		ss.submit()
		self.assertEqual(ss.total_loan_repayment, 582)
		self.assertEqual(ss.net_pay, (flt(ss.gross_pay) - (flt(ss.total_deduction) + flt(ss.total_loan_repayment))))

	def test_payroll_frequency(self):
		fiscal_year = get_fiscal_year(nowdate(), company=erpnext.get_default_company())[0]
		month = "%02d" % getdate(nowdate()).month
		m = get_month_details(fiscal_year, month)

		for payroll_frequncy in ["Monthly", "Bimonthly", "Fortnightly", "Weekly", "Daily"]:
			make_employee(payroll_frequncy + "_test_employee@salary.com")
			ss = make_employee_salary_slip(payroll_frequncy + "_test_employee@salary.com", payroll_frequncy)
			if payroll_frequncy == "Monthly":
				self.assertEqual(ss.end_date, m['month_end_date'])
			elif payroll_frequncy == "Bimonthly":
				if getdate(ss.start_date).day <= 15:
					self.assertEqual(ss.end_date, m['month_mid_end_date'])
				else:
					self.assertEqual(ss.end_date, m['month_end_date'])
			elif payroll_frequncy == "Fortnightly":
				self.assertEqual(ss.end_date, add_days(nowdate(),13))
			elif payroll_frequncy == "Weekly":
				self.assertEqual(ss.end_date, add_days(nowdate(),6))
			elif payroll_frequncy == "Daily":
				self.assertEqual(ss.end_date, nowdate())

	def make_holiday_list(self):
		fiscal_year = get_fiscal_year(nowdate(), company=erpnext.get_default_company())
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


def make_employee_salary_slip(user, payroll_frequency, salary_structure=None):
	from erpnext.hr.doctype.salary_structure.test_salary_structure import make_salary_structure
	if not salary_structure:
		salary_structure = payroll_frequency + " Salary Structure Test for Salary Slip"
	employee = frappe.db.get_value("Employee", {"user_id": user})
	salary_structure_doc = make_salary_structure(salary_structure, payroll_frequency, employee)
	salary_slip = frappe.db.get_value("Salary Slip", {"employee": frappe.db.get_value("Employee", {"user_id": user})})

	if not salary_slip:
		salary_slip = make_salary_slip(salary_structure_doc.name, employee = employee)
		salary_slip.employee_name = frappe.get_value("Employee", {"name":frappe.db.get_value("Employee", {"user_id": user})}, "employee_name")
		salary_slip.payroll_frequency = payroll_frequency
		salary_slip.posting_date = nowdate()
		salary_slip.insert()
		# salary_slip.submit()
		# salary_slip = salary_slip.name

	return salary_slip


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

def get_salary_component_account(sal_comp):
	company = erpnext.get_default_company()
	sal_comp = frappe.get_doc("Salary Component", sal_comp)
	sal_comp.append("accounts", {
		"company": company,
		"default_account": create_account(company)
	})
	sal_comp.save()


def create_account(company):
	salary_account = frappe.db.get_value("Account", "Salary - " + frappe.db.get_value('Company', company, 'abbr'))
	if not salary_account:
		frappe.get_doc({
		"doctype": "Account",
		"account_name": "Salary",
		"parent_account": "Indirect Expenses - " + frappe.db.get_value('Company', company, 'abbr'),
		"company": company
		}).insert()
	return salary_account


def get_earnings_component(setup=False):
	if setup:
		make_earning_salary_component(["Basic Salary", "Special Allowance", "HRA"])

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

def get_deductions_component(setup=False):
	if setup:
		make_deduction_salary_component(["Professional Tax", "TDS"])

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
