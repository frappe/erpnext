# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import calendar
import random
import unittest

import frappe
from frappe.utils import (
	add_days,
	add_months,
	cstr,
	flt,
	get_first_day,
	get_last_day,
	getdate,
	nowdate,
)
from frappe.utils.make_random import get_random

import erpnext
from erpnext.accounts.utils import get_fiscal_year
from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.doctype.leave_allocation.test_leave_allocation import create_leave_allocation
from erpnext.hr.doctype.leave_type.test_leave_type import create_leave_type
from erpnext.payroll.doctype.employee_tax_exemption_declaration.test_employee_tax_exemption_declaration import (
	create_exemption_category,
	create_payroll_period,
)
from erpnext.payroll.doctype.payroll_entry.payroll_entry import get_month_details
from erpnext.payroll.doctype.salary_structure.salary_structure import make_salary_slip


class TestSalarySlip(unittest.TestCase):
	def setUp(self):
		setup_test()

	def tearDown(self):
		frappe.db.set_value("Payroll Settings", None, "include_holidays_in_total_working_days", 0)
		frappe.set_user("Administrator")

	def test_payment_days_based_on_attendance(self):
		from erpnext.hr.doctype.attendance.attendance import mark_attendance
		no_of_days = self.get_no_of_days()

		# Payroll based on attendance
		frappe.db.set_value("Payroll Settings", None, "payroll_based_on", "Attendance")
		frappe.db.set_value("Payroll Settings", None, "daily_wages_fraction_for_half_day", 0.75)

		emp_id = make_employee("test_payment_days_based_on_attendance@salary.com")
		frappe.db.set_value("Employee", emp_id, {"relieving_date": None, "status": "Active"})

		frappe.db.set_value("Leave Type", "Leave Without Pay", "include_holiday", 0)

		month_start_date = get_first_day(nowdate())
		month_end_date = get_last_day(nowdate())

		first_sunday = frappe.db.sql("""
			select holiday_date from `tabHoliday`
			where parent = 'Salary Slip Test Holiday List'
				and holiday_date between %s and %s
			order by holiday_date
		""", (month_start_date, month_end_date))[0][0]

		mark_attendance(emp_id, first_sunday, 'Absent', ignore_validate=True) # invalid lwp
		mark_attendance(emp_id, add_days(first_sunday, 1), 'Absent', ignore_validate=True) # counted as absent
		mark_attendance(emp_id, add_days(first_sunday, 2), 'Half Day', leave_type='Leave Without Pay', ignore_validate=True) # valid 0.75 lwp
		mark_attendance(emp_id, add_days(first_sunday, 3), 'On Leave', leave_type='Leave Without Pay', ignore_validate=True) # valid lwp
		mark_attendance(emp_id, add_days(first_sunday, 4), 'On Leave', leave_type='Casual Leave', ignore_validate=True) # invalid lwp
		mark_attendance(emp_id, add_days(first_sunday, 7), 'On Leave', leave_type='Leave Without Pay', ignore_validate=True) # invalid lwp

		ss = make_employee_salary_slip("test_payment_days_based_on_attendance@salary.com", "Monthly", "Test Payment Based On Attendence")

		self.assertEqual(ss.leave_without_pay, 1.25)
		self.assertEqual(ss.absent_days, 1)

		days_in_month = no_of_days[0]
		no_of_holidays = no_of_days[1]

		self.assertEqual(ss.payment_days, days_in_month - no_of_holidays - 2.25)

		#Gross pay calculation based on attendances
		gross_pay = 78000 - ((78000 / (days_in_month - no_of_holidays)) * flt(ss.leave_without_pay + ss.absent_days))

		self.assertEqual(ss.gross_pay, gross_pay)

		frappe.db.set_value("Payroll Settings", None, "payroll_based_on", "Leave")

	def test_payment_days_based_on_leave_application(self):
		no_of_days = self.get_no_of_days()

		# Payroll based on attendance
		frappe.db.set_value("Payroll Settings", None, "payroll_based_on", "Leave")

		emp_id = make_employee("test_payment_days_based_on_leave_application@salary.com")
		frappe.db.set_value("Employee", emp_id, {"relieving_date": None, "status": "Active"})

		frappe.db.set_value("Leave Type", "Leave Without Pay", "include_holiday", 0)

		month_start_date = get_first_day(nowdate())
		month_end_date = get_last_day(nowdate())

		first_sunday = frappe.db.sql("""
			select holiday_date from `tabHoliday`
			where parent = 'Salary Slip Test Holiday List'
				and holiday_date between %s and %s
			order by holiday_date
		""", (month_start_date, month_end_date))[0][0]

		make_leave_application(emp_id, first_sunday, add_days(first_sunday, 3), "Leave Without Pay")

		leave_type_ppl = create_leave_type(leave_type_name="Test Partially Paid Leave", is_ppl = 1)
		leave_type_ppl.save()

		alloc = create_leave_allocation(
			employee = emp_id, from_date = add_days(first_sunday, 4),
			to_date = add_days(first_sunday, 10), new_leaves_allocated = 3,
			leave_type = "Test Partially Paid Leave")
		alloc.save()
		alloc.submit()

		#two day leave ppl with fraction_of_daily_salary_per_leave = 0.5 equivalent to single day lwp
		make_leave_application(emp_id, add_days(first_sunday, 4), add_days(first_sunday, 5), "Test Partially Paid Leave")

		ss = make_employee_salary_slip("test_payment_days_based_on_leave_application@salary.com", "Monthly", "Test Payment Based On Leave Application")


		self.assertEqual(ss.leave_without_pay, 4)

		days_in_month = no_of_days[0]
		no_of_holidays = no_of_days[1]

		self.assertEqual(ss.payment_days, days_in_month - no_of_holidays - 4)

		frappe.db.set_value("Payroll Settings", None, "payroll_based_on", "Leave")

	def test_component_amount_dependent_on_another_payment_days_based_component(self):
		from erpnext.hr.doctype.attendance.attendance import mark_attendance
		from erpnext.payroll.doctype.salary_structure.test_salary_structure import (
			create_salary_structure_assignment,
		)

		# Payroll based on attendance
		frappe.db.set_value("Payroll Settings", None, "payroll_based_on", "Attendance")

		salary_structure = make_salary_structure_for_payment_days_based_component_dependency()
		employee = make_employee("test_payment_days_based_component@salary.com", company="_Test Company")

		# base = 50000
		create_salary_structure_assignment(employee, salary_structure.name, company="_Test Company", currency="INR")

		# mark employee absent for a day since this case works fine if payment days are equal to working days
		month_start_date = get_first_day(nowdate())
		month_end_date = get_last_day(nowdate())

		first_sunday = frappe.db.sql("""
			select holiday_date from `tabHoliday`
			where parent = 'Salary Slip Test Holiday List'
				and holiday_date between %s and %s
			order by holiday_date
		""", (month_start_date, month_end_date))[0][0]

		mark_attendance(employee, add_days(first_sunday, 1), 'Absent', ignore_validate=True) # counted as absent

		# make salary slip and assert payment days
		ss = make_salary_slip_for_payment_days_dependency_test("test_payment_days_based_component@salary.com", salary_structure.name)
		self.assertEqual(ss.absent_days, 1)

		ss.reload()
		payment_days_based_comp_amount = 0
		for component in ss.earnings:
			if component.salary_component == "HRA - Payment Days":
				payment_days_based_comp_amount = flt(component.amount, component.precision("amount"))
				break

		# check if the dependent component is calculated using the amount updated after payment days
		actual_amount = 0
		precision = 0
		for component in ss.deductions:
			if component.salary_component == "P - Employee Provident Fund":
				precision = component.precision("amount")
				actual_amount = flt(component.amount, precision)
				break

		expected_amount = flt((flt(ss.gross_pay) - payment_days_based_comp_amount) * 0.12, precision)

		self.assertEqual(actual_amount, expected_amount)
		frappe.db.set_value("Payroll Settings", None, "payroll_based_on", "Leave")

	def test_salary_slip_with_holidays_included(self):
		no_of_days = self.get_no_of_days()
		frappe.db.set_value("Payroll Settings", None, "include_holidays_in_total_working_days", 1)
		make_employee("test_salary_slip_with_holidays_included@salary.com")
		frappe.db.set_value("Employee", frappe.get_value("Employee",
			{"employee_name":"test_salary_slip_with_holidays_included@salary.com"}, "name"), "relieving_date", None)
		frappe.db.set_value("Employee", frappe.get_value("Employee",
			{"employee_name":"test_salary_slip_with_holidays_included@salary.com"}, "name"), "status", "Active")
		ss = make_employee_salary_slip("test_salary_slip_with_holidays_included@salary.com", "Monthly", "Test Salary Slip With Holidays Included")

		self.assertEqual(ss.total_working_days, no_of_days[0])
		self.assertEqual(ss.payment_days, no_of_days[0])
		self.assertEqual(ss.earnings[0].amount, 50000)
		self.assertEqual(ss.earnings[1].amount, 3000)
		self.assertEqual(ss.gross_pay, 78000)

	def test_salary_slip_with_holidays_excluded(self):
		no_of_days = self.get_no_of_days()
		frappe.db.set_value("Payroll Settings", None, "include_holidays_in_total_working_days", 0)
		make_employee("test_salary_slip_with_holidays_excluded@salary.com")
		frappe.db.set_value("Employee", frappe.get_value("Employee",
			{"employee_name":"test_salary_slip_with_holidays_excluded@salary.com"}, "name"), "relieving_date", None)
		frappe.db.set_value("Employee", frappe.get_value("Employee",
			{"employee_name":"test_salary_slip_with_holidays_excluded@salary.com"}, "name"), "status", "Active")
		ss = make_employee_salary_slip("test_salary_slip_with_holidays_excluded@salary.com", "Monthly",  "Test Salary Slip With Holidays Excluded")

		self.assertEqual(ss.total_working_days, no_of_days[0] - no_of_days[1])
		self.assertEqual(ss.payment_days, no_of_days[0] - no_of_days[1])
		self.assertEqual(ss.earnings[0].amount, 50000)
		self.assertEqual(ss.earnings[0].default_amount, 50000)
		self.assertEqual(ss.earnings[1].amount, 3000)
		self.assertEqual(ss.gross_pay, 78000)

	def test_payment_days(self):
		from erpnext.payroll.doctype.salary_structure.test_salary_structure import (
			create_salary_structure_assignment,
		)

		no_of_days = self.get_no_of_days()
		# Holidays not included in working days
		frappe.db.set_value("Payroll Settings", None, "include_holidays_in_total_working_days", 1)

		# set joinng date in the same month
		employee = make_employee("test_payment_days@salary.com")
		if getdate(nowdate()).day >= 15:
			relieving_date = getdate(add_days(nowdate(),-10))
			date_of_joining = getdate(add_days(nowdate(),-10))
		elif getdate(nowdate()).day < 15 and getdate(nowdate()).day >= 5:
			date_of_joining = getdate(add_days(nowdate(),-3))
			relieving_date = getdate(add_days(nowdate(),-3))
		elif getdate(nowdate()).day < 5 and not getdate(nowdate()).day == 1:
			date_of_joining = getdate(add_days(nowdate(),-1))
			relieving_date = getdate(add_days(nowdate(),-1))
		elif getdate(nowdate()).day == 1:
			date_of_joining = getdate(nowdate())
			relieving_date = getdate(nowdate())

		frappe.db.set_value("Employee", employee, {
			"date_of_joining": date_of_joining,
			"relieving_date": None,
			"status": "Active"
		})

		salary_structure = "Test Payment Days"
		ss = make_employee_salary_slip("test_payment_days@salary.com", "Monthly", salary_structure)

		self.assertEqual(ss.total_working_days, no_of_days[0])
		self.assertEqual(ss.payment_days, (no_of_days[0] - getdate(date_of_joining).day + 1))

		# set relieving date in the same month
		frappe.db.set_value("Employee", employee, {
			"date_of_joining": add_days(nowdate(),-60),
			"relieving_date": relieving_date,
			"status": "Left"
		})

		if date_of_joining.day > 1:
			self.assertRaises(frappe.ValidationError, ss.save)

		create_salary_structure_assignment(employee, salary_structure)
		ss.reload()
		ss.save()

		self.assertEqual(ss.total_working_days, no_of_days[0])
		self.assertEqual(ss.payment_days, getdate(relieving_date).day)

		frappe.db.set_value("Employee", frappe.get_value("Employee",
			{"employee_name":"test_payment_days@salary.com"}, "name"), "relieving_date", None)
		frappe.db.set_value("Employee", frappe.get_value("Employee",
			{"employee_name":"test_payment_days@salary.com"}, "name"), "status", "Active")

	def test_employee_salary_slip_read_permission(self):
		make_employee("test_employee_salary_slip_read_permission@salary.com")

		salary_slip_test_employee = make_employee_salary_slip("test_employee_salary_slip_read_permission@salary.com", "Monthly", "Test Employee Salary Slip Read Permission")
		frappe.set_user("test_employee_salary_slip_read_permission@salary.com")
		self.assertTrue(salary_slip_test_employee.has_permission("read"))

	def test_email_salary_slip(self):
		frappe.db.sql("delete from `tabEmail Queue`")

		frappe.db.set_value("Payroll Settings", None, "email_salary_slip_to_employee", 1)

		make_employee("test_email_salary_slip@salary.com")
		ss = make_employee_salary_slip("test_email_salary_slip@salary.com", "Monthly", "Test Salary Slip Email")
		ss.company = "_Test Company"
		ss.save()
		ss.submit()

		email_queue = frappe.db.sql("""select name from `tabEmail Queue`""")
		self.assertTrue(email_queue)

	def test_loan_repayment_salary_slip(self):
		from erpnext.loan_management.doctype.loan.test_loan import (
			create_loan,
			create_loan_accounts,
			create_loan_type,
			make_loan_disbursement_entry,
		)
		from erpnext.loan_management.doctype.process_loan_interest_accrual.process_loan_interest_accrual import (
			process_loan_interest_accrual_for_term_loans,
		)
		from erpnext.payroll.doctype.salary_structure.test_salary_structure import make_salary_structure

		applicant = make_employee("test_loan_repayment_salary_slip@salary.com", company="_Test Company")

		create_loan_accounts()

		create_loan_type("Car Loan", 500000, 8.4,
			is_term_loan=1,
			mode_of_payment='Cash',
			payment_account='Payment Account - _TC',
			loan_account='Loan Account - _TC',
			interest_income_account='Interest Income Account - _TC',
			penalty_income_account='Penalty Income Account - _TC')

		payroll_period = create_payroll_period(name="_Test Payroll Period 1", company="_Test Company")

		make_salary_structure("Test Loan Repayment Salary Structure", "Monthly", employee=applicant, currency='INR',
			payroll_period=payroll_period)

		frappe.db.sql("delete from tabLoan")
		loan = create_loan(applicant, "Car Loan", 11000, "Repay Over Number of Periods", 20, posting_date=add_months(nowdate(), -1))
		loan.repay_from_salary = 1
		loan.submit()

		make_loan_disbursement_entry(loan.name, loan.loan_amount, disbursement_date=add_months(nowdate(), -1))

		process_loan_interest_accrual_for_term_loans(posting_date=nowdate())

		ss = make_employee_salary_slip("test_loan_repayment_salary_slip@salary.com", "Monthly", "Test Loan Repayment Salary Structure")
		ss.submit()

		self.assertEqual(ss.total_loan_repayment, 592)
		self.assertEqual(ss.net_pay, (flt(ss.gross_pay) - (flt(ss.total_deduction) + flt(ss.total_loan_repayment))))

	def test_payroll_frequency(self):
		fiscal_year = get_fiscal_year(nowdate(), company=erpnext.get_default_company())[0]
		month = "%02d" % getdate(nowdate()).month
		m = get_month_details(fiscal_year, month)

		for payroll_frequency in ["Monthly", "Bimonthly", "Fortnightly", "Weekly", "Daily"]:
			make_employee(payroll_frequency + "_test_employee@salary.com")
			ss = make_employee_salary_slip(payroll_frequency + "_test_employee@salary.com", payroll_frequency, payroll_frequency + "_Test Payroll Frequency")
			if payroll_frequency == "Monthly":
				self.assertEqual(ss.end_date, m['month_end_date'])
			elif payroll_frequency == "Bimonthly":
				if getdate(ss.start_date).day <= 15:
					self.assertEqual(ss.end_date, m['month_mid_end_date'])
				else:
					self.assertEqual(ss.end_date, m['month_end_date'])
			elif payroll_frequency == "Fortnightly":
				self.assertEqual(ss.end_date, add_days(nowdate(),13))
			elif payroll_frequency == "Weekly":
				self.assertEqual(ss.end_date, add_days(nowdate(),6))
			elif payroll_frequency == "Daily":
				self.assertEqual(ss.end_date, nowdate())

	def test_multi_currency_salary_slip(self):
		from erpnext.payroll.doctype.salary_structure.test_salary_structure import make_salary_structure

		applicant = make_employee("test_multi_currency_salary_slip@salary.com", company="_Test Company")
		frappe.db.sql("""delete from `tabSalary Structure` where name='Test Multi Currency Salary Slip'""")
		salary_structure = make_salary_structure("Test Multi Currency Salary Slip", "Monthly", employee=applicant, company="_Test Company", currency='USD')
		salary_slip = make_salary_slip(salary_structure.name, employee = applicant)
		salary_slip.exchange_rate = 70
		salary_slip.calculate_net_pay()

		self.assertEqual(salary_slip.gross_pay, 78000)
		self.assertEqual(salary_slip.base_gross_pay, 78000*70)

	def test_year_to_date_computation(self):
		from erpnext.payroll.doctype.salary_structure.test_salary_structure import make_salary_structure

		applicant = make_employee("test_ytd@salary.com", company="_Test Company")

		payroll_period = create_payroll_period(name="_Test Payroll Period 1", company="_Test Company")

		create_tax_slab(payroll_period, allow_tax_exemption=True, currency="INR", effective_date=getdate("2019-04-01"),
			company="_Test Company")

		salary_structure = make_salary_structure("Monthly Salary Structure Test for Salary Slip YTD",
			"Monthly", employee=applicant, company="_Test Company", currency="INR", payroll_period=payroll_period)

		# clear salary slip for this employee
		frappe.db.sql("DELETE FROM `tabSalary Slip` where employee_name = 'test_ytd@salary.com'")

		create_salary_slips_for_payroll_period(applicant, salary_structure.name,
			payroll_period, deduct_random=False, num=6)

		salary_slips = frappe.get_all('Salary Slip', fields=['year_to_date', 'net_pay'], filters={'employee_name':
			'test_ytd@salary.com'}, order_by = 'posting_date')

		year_to_date = 0
		for slip in salary_slips:
			year_to_date += flt(slip.net_pay)
			self.assertEqual(slip.year_to_date, year_to_date)

	def test_component_wise_year_to_date_computation(self):
		from erpnext.payroll.doctype.salary_structure.test_salary_structure import make_salary_structure

		employee_name = "test_component_wise_ytd@salary.com"
		applicant = make_employee(employee_name, company="_Test Company")

		payroll_period = create_payroll_period(name="_Test Payroll Period 1", company="_Test Company")

		create_tax_slab(payroll_period, allow_tax_exemption=True, currency="INR", effective_date=getdate("2019-04-01"),
			company="_Test Company")

		salary_structure = make_salary_structure("Monthly Salary Structure Test for Salary Slip YTD",
			"Monthly", employee=applicant, company="_Test Company", currency="INR", payroll_period=payroll_period)

		# clear salary slip for this employee
		frappe.db.sql("DELETE FROM `tabSalary Slip` where employee_name = '%s'" % employee_name)

		create_salary_slips_for_payroll_period(applicant, salary_structure.name,
			payroll_period, deduct_random=False, num=3)

		salary_slips = frappe.get_all("Salary Slip", fields=["name"], filters={"employee_name":
			employee_name}, order_by="posting_date")

		year_to_date = dict()
		for slip in salary_slips:
			doc = frappe.get_doc("Salary Slip", slip.name)
			for entry in doc.get("earnings"):
				if not year_to_date.get(entry.salary_component):
					year_to_date[entry.salary_component] = 0

				year_to_date[entry.salary_component] += entry.amount
				self.assertEqual(year_to_date[entry.salary_component], entry.year_to_date)

	def test_tax_for_payroll_period(self):
		data = {}
		# test the impact of tax exemption declaration, tax exemption proof submission
		# and deduct check boxes in annual tax calculation
		# as per assigned salary structure 40500 in monthly salary so 236000*5/100/12
		frappe.db.sql("""delete from `tabPayroll Period`""")
		frappe.db.sql("""delete from `tabSalary Component`""")

		payroll_period = create_payroll_period()

		create_tax_slab(payroll_period, allow_tax_exemption=True)

		employee = make_employee("test_tax@salary.slip")
		delete_docs = [
			"Salary Slip",
			"Additional Salary",
			"Employee Tax Exemption Declaration",
			"Employee Tax Exemption Proof Submission",
			"Employee Benefit Claim",
			"Salary Structure Assignment"
		]
		for doc in delete_docs:
			frappe.db.sql("delete from `tab%s` where employee='%s'" % (doc, employee))

		from erpnext.payroll.doctype.salary_structure.test_salary_structure import make_salary_structure

		salary_structure = make_salary_structure("Stucture to test tax", "Monthly",
			other_details={"max_benefits": 100000}, test_tax=True,
			employee=employee, payroll_period=payroll_period)

		# create salary slip for whole period deducting tax only on last period
		# to find the total tax amount paid
		create_salary_slips_for_payroll_period(employee, salary_structure.name,
			payroll_period, deduct_random=False)
		tax_paid = get_tax_paid_in_period(employee)

		annual_tax = 113589.0
		try:
			self.assertEqual(tax_paid, annual_tax)
		except AssertionError:
			print("\nSalary Slip - Annual tax calculation failed\n")
			raise
		frappe.db.sql("""delete from `tabSalary Slip` where employee=%s""", (employee))

		# create exemption declaration so the tax amount varies
		create_exemption_declaration(employee, payroll_period.name)

		# create for payroll deducting in random months
		data["deducted_dates"] = create_salary_slips_for_payroll_period(employee,
			salary_structure.name, payroll_period)
		tax_paid = get_tax_paid_in_period(employee)

		# No proof, benefit claim sumitted, total tax paid, should not change
		try:
			self.assertEqual(tax_paid, annual_tax)
		except AssertionError:
			print("\nSalary Slip - Tax calculation failed on following case\n", data, "\n")
			raise

		# Submit proof for total 120000
		data["proof"] = create_proof_submission(employee, payroll_period, 120000)

		# Submit benefit claim for total 50000
		data["benefit-1"] = create_benefit_claim(employee, payroll_period, 15000, "Medical Allowance")
		data["benefit-2"] = create_benefit_claim(employee, payroll_period, 35000, "Leave Travel Allowance")


		frappe.db.sql("""delete from `tabSalary Slip` where employee=%s""", (employee))
		data["deducted_dates"] = create_salary_slips_for_payroll_period(employee,
			salary_structure.name, payroll_period)
		tax_paid = get_tax_paid_in_period(employee)

		# total taxable income 416000, 166000 @ 5% ie. 8300
		try:
			self.assertEqual(tax_paid, 82389.0)
		except AssertionError:
			print("\nSalary Slip - Tax calculation failed on following case\n", data, "\n")
			raise

		# create additional salary of 150000
		frappe.db.sql("""delete from `tabSalary Slip` where employee=%s""", (employee))
		data["additional-1"] = create_additional_salary(employee, payroll_period, 150000)
		data["deducted_dates"] = create_salary_slips_for_payroll_period(employee,
			salary_structure.name, payroll_period)

		# total taxable income 566000, 250000 @ 5%, 66000 @ 20%, 12500 + 13200
		tax_paid = get_tax_paid_in_period(employee)
		try:
			self.assertEqual(tax_paid, annual_tax)
		except AssertionError:
			print("\nSalary Slip - Tax calculation failed on following case\n", data, "\n")
			raise
		frappe.db.sql("""delete from `tabAdditional Salary` where employee=%s""", (employee))

		# undelete fixture data
		frappe.db.rollback()

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
	from erpnext.payroll.doctype.salary_structure.test_salary_structure import make_salary_structure

	if not salary_structure:
		salary_structure = payroll_frequency + " Salary Structure Test for Salary Slip"

	employee = frappe.db.get_value("Employee",
					{
						"user_id": user
					},
					["name", "company", "employee_name"],
					as_dict=True)

	salary_structure_doc = make_salary_structure(salary_structure, payroll_frequency, employee=employee.name, company=employee.company)
	salary_slip_name = frappe.db.get_value("Salary Slip", {"employee": frappe.db.get_value("Employee", {"user_id": user})})

	if not salary_slip_name:
		salary_slip = make_salary_slip(salary_structure_doc.name, employee = employee.name)
		salary_slip.employee_name = employee.employee_name
		salary_slip.payroll_frequency = payroll_frequency
		salary_slip.posting_date = nowdate()
		salary_slip.insert()
	else:
		salary_slip = frappe.get_doc('Salary Slip', salary_slip_name)

	return salary_slip

def make_salary_component(salary_components, test_tax, company_list=None):
	for salary_component in salary_components:
		if not frappe.db.exists('Salary Component', salary_component["salary_component"]):
			if test_tax:
				if salary_component["type"] == "Earning":
					salary_component["is_tax_applicable"] = 1
				elif salary_component["salary_component"] == "TDS":
					salary_component["variable_based_on_taxable_salary"] = 1
					salary_component["amount_based_on_formula"] = 0
					salary_component["amount"] = 0
					salary_component["formula"] = ""
					salary_component["condition"] = ""
			salary_component["doctype"] = "Salary Component"
			salary_component["salary_component_abbr"] = salary_component["abbr"]
			frappe.get_doc(salary_component).insert()
		get_salary_component_account(salary_component["salary_component"], company_list)

def get_salary_component_account(sal_comp, company_list=None):
	company = erpnext.get_default_company()

	if company_list and company not in company_list:
		company_list.append(company)

	sal_comp = frappe.get_doc("Salary Component", sal_comp)
	if not sal_comp.get("accounts"):
		for d in company_list:
			company_abbr = frappe.get_cached_value('Company', d, 'abbr')

			if sal_comp.type == "Earning":
				account_name = "Salary"
				parent_account = "Indirect Expenses - " + company_abbr
			else:
				account_name = "Salary Deductions"
				parent_account = "Current Liabilities - " + company_abbr

			sal_comp.append("accounts", {
				"company": d,
				"account": create_account(account_name, d, parent_account)
			})
			sal_comp.save()

def create_account(account_name, company, parent_account):
	company_abbr = frappe.get_cached_value('Company',  company,  'abbr')
	account = frappe.db.get_value("Account", account_name + " - " + company_abbr)
	if not account:
		frappe.get_doc({
			"doctype": "Account",
			"account_name": account_name,
			"parent_account": parent_account,
			"company": company
		}).insert()
	return account

def make_earning_salary_component(setup=False, test_tax=False, company_list=None):
	data = [
		{
			"salary_component": 'Basic Salary',
			"abbr":'BS',
			"condition": 'base > 10000',
			"formula": 'base',
			"type": "Earning",
			"amount_based_on_formula": 1
		},
		{
			"salary_component": 'HRA',
			"abbr":'H',
			"amount": 3000,
			"type": "Earning"
		},
		{
			"salary_component": 'Special Allowance',
			"abbr":'SA',
			"condition": 'H < 10000',
			"formula": 'BS*.5',
			"type": "Earning",
			"amount_based_on_formula": 1
		},
		{
			"salary_component": "Leave Encashment",
			"abbr": 'LE',
			"type": "Earning"
		}
	]
	if test_tax:
		data.extend([
			{
				"salary_component": "Leave Travel Allowance",
				"abbr": 'B',
				"is_flexible_benefit": 1,
				"type": "Earning",
				"pay_against_benefit_claim": 1,
				"max_benefit_amount": 100000,
				"depends_on_payment_days": 0
			},
			{
				"salary_component": "Medical Allowance",
				"abbr": 'B',
				"is_flexible_benefit": 1,
				"pay_against_benefit_claim": 0,
				"type": "Earning",
				"max_benefit_amount": 15000
			},
			{
				"salary_component": "Performance Bonus",
				"abbr": 'B',
				"type": "Earning"
			}
		])
	if setup or test_tax:
		make_salary_component(data, test_tax, company_list)
	data.append({
		"salary_component": 'Basic Salary',
		"abbr":'BS',
		"condition": 'base < 10000',
		"formula": 'base*.2',
		"type": "Earning",
		"amount_based_on_formula": 1
	})
	return data

def make_deduction_salary_component(setup=False, test_tax=False, company_list=None):
	data =  [
		{
			"salary_component": 'Professional Tax',
			"abbr":'PT',
			"type": "Deduction",
			"amount": 200,
			"exempted_from_income_tax": 1

		}
	]
	if not test_tax:
		data.append({
			"salary_component": 'TDS',
			"abbr":'T',
			"condition": 'employment_type=="Intern"',
			"type": "Deduction",
			"round_to_the_nearest_integer": 1
		})
	else:
		data.append({
			"salary_component": 'TDS',
			"abbr":'T',
			"type": "Deduction",
			"depends_on_payment_days": 0,
			"variable_based_on_taxable_salary": 1,
			"round_to_the_nearest_integer": 1
		})
	if setup or test_tax:
		make_salary_component(data, test_tax, company_list)

	return data

def get_tax_paid_in_period(employee):
	tax_paid_amount = frappe.db.sql("""select sum(sd.amount) from `tabSalary Detail`
		sd join `tabSalary Slip` ss where ss.name=sd.parent and ss.employee=%s
		and ss.docstatus=1 and sd.salary_component='TDS'""", (employee))
	return tax_paid_amount[0][0]

def create_exemption_declaration(employee, payroll_period):
	create_exemption_category()
	declaration = frappe.get_doc({
		"doctype": "Employee Tax Exemption Declaration",
		"employee": employee,
		"payroll_period": payroll_period,
		"company": erpnext.get_default_company(),
		"currency": erpnext.get_default_currency()
	})
	declaration.append("declarations", {
		"exemption_sub_category": "_Test Sub Category",
		"exemption_category": "_Test Category",
		"amount": 100000
	})
	declaration.submit()

def create_proof_submission(employee, payroll_period, amount):
	submission_date = add_months(payroll_period.start_date, random.randint(0, 11))
	proof_submission = frappe.get_doc({
		"doctype": "Employee Tax Exemption Proof Submission",
		"employee": employee,
		"payroll_period": payroll_period.name,
		"submission_date": submission_date,
		"currency": erpnext.get_default_currency()
	})
	proof_submission.append("tax_exemption_proofs", {
		"exemption_sub_category": "_Test Sub Category",
		"exemption_category": "_Test Category",
		"type_of_proof": "Test", "amount": amount
	})
	proof_submission.submit()
	return submission_date

def create_benefit_claim(employee, payroll_period, amount, component):
	claim_date = add_months(payroll_period.start_date, random.randint(0, 11))
	frappe.get_doc({
		"doctype": "Employee Benefit Claim",
		"employee": employee,
		"claimed_amount": amount,
		"claim_date": claim_date,
		"earning_component": component,
		"currency": erpnext.get_default_currency()
	}).submit()
	return claim_date

def create_tax_slab(payroll_period, effective_date = None, allow_tax_exemption = False, dont_submit = False, currency=None,
	company=None):
	if not currency:
		currency = erpnext.get_default_currency()

	if company:
		currency = erpnext.get_company_currency(company)

	slabs = [
		{
			"from_amount": 250000,
			"to_amount": 500000,
			"percent_deduction": 5,
			"condition": "annual_taxable_earning > 500000"
		},
		{
			"from_amount": 500001,
			"to_amount": 1000000,
			"percent_deduction": 20
		},
		{
			"from_amount": 1000001,
			"percent_deduction": 30
		}
	]

	income_tax_slab_name = frappe.db.get_value("Income Tax Slab", {"currency": currency})
	if not income_tax_slab_name:
		income_tax_slab = frappe.new_doc("Income Tax Slab")
		income_tax_slab.name = "Tax Slab: " + payroll_period.name + " " + cstr(currency)
		income_tax_slab.effective_from = effective_date or add_days(payroll_period.start_date, -2)
		income_tax_slab.company = company or ''
		income_tax_slab.currency = currency

		if allow_tax_exemption:
			income_tax_slab.allow_tax_exemption = 1
			income_tax_slab.standard_tax_exemption_amount = 50000

		for item in slabs:
			income_tax_slab.append("slabs", item)

		income_tax_slab.append("other_taxes_and_charges", {
			"description": "cess",
			"percent": 4
		})

		income_tax_slab.save()
		if not dont_submit:
			income_tax_slab.submit()

		return income_tax_slab.name
	else:
		return income_tax_slab_name

def create_salary_slips_for_payroll_period(employee, salary_structure, payroll_period, deduct_random=True, num=12):
	deducted_dates = []
	i = 0
	while i < num:
		slip = frappe.get_doc({"doctype": "Salary Slip", "employee": employee,
				"salary_structure": salary_structure, "frequency": "Monthly"})
		if i == 0:
			posting_date = add_days(payroll_period.start_date, 25)
		else:
			posting_date = add_months(posting_date, 1)
		if i == 11:
			slip.deduct_tax_for_unsubmitted_tax_exemption_proof = 1
			slip.deduct_tax_for_unclaimed_employee_benefits = 1
		if deduct_random and not random.randint(0, 2):
			slip.deduct_tax_for_unsubmitted_tax_exemption_proof = 1
			deducted_dates.append(posting_date)
		slip.posting_date = posting_date
		slip.start_date = get_first_day(posting_date)
		slip.end_date = get_last_day(posting_date)
		doc = make_salary_slip(salary_structure, slip, employee)
		doc.submit()
		i += 1
	return deducted_dates

def create_additional_salary(employee, payroll_period, amount):
	salary_date = add_months(payroll_period.start_date, random.randint(0, 11))
	frappe.get_doc({
		"doctype": "Additional Salary",
		"employee": employee,
		"company": erpnext.get_default_company(),
		"salary_component": "Performance Bonus",
		"payroll_date": salary_date,
		"amount": amount,
		"type": "Earning",
		"currency": erpnext.get_default_currency()
	}).submit()
	return salary_date

def make_leave_application(employee, from_date, to_date, leave_type, company=None):
	leave_application = frappe.get_doc(dict(
		doctype = 'Leave Application',
		employee = employee,
		leave_type = leave_type,
		from_date = from_date,
		to_date = to_date,
		company = company or erpnext.get_default_company() or "_Test Company",
		docstatus = 1,
		status = "Approved",
		leave_approver = 'test@example.com'
	))
	leave_application.submit()

def setup_test():
	make_earning_salary_component(setup=True, company_list=["_Test Company"])
	make_deduction_salary_component(setup=True, company_list=["_Test Company"])

	for dt in ["Leave Application", "Leave Allocation", "Salary Slip", "Attendance", "Additional Salary"]:
		frappe.db.sql("delete from `tab%s`" % dt)

	make_holiday_list()

	frappe.db.set_value("Company", erpnext.get_default_company(), "default_holiday_list", "Salary Slip Test Holiday List")
	frappe.db.set_value("Payroll Settings", None, "email_salary_slip_to_employee", 0)
	frappe.db.set_value('HR Settings', None, 'leave_status_notification_template', None)
	frappe.db.set_value('HR Settings', None, 'leave_approval_notification_template', None)

def make_holiday_list():
	fiscal_year = get_fiscal_year(nowdate(), company=erpnext.get_default_company())
	holiday_list = frappe.db.exists("Holiday List", "Salary Slip Test Holiday List")
	if not holiday_list:
		holiday_list = frappe.get_doc({
			"doctype": "Holiday List",
			"holiday_list_name": "Salary Slip Test Holiday List",
			"from_date": fiscal_year[1],
			"to_date": fiscal_year[2],
			"weekly_off": "Sunday"
		}).insert()
		holiday_list.get_weekly_off_dates()
		holiday_list.save()
		holiday_list = holiday_list.name

	return holiday_list

def make_salary_structure_for_payment_days_based_component_dependency():
	earnings = [
		{
			"salary_component": "Basic Salary - Payment Days",
			"abbr": "P_BS",
			"type": "Earning",
			"formula": "base",
			"amount_based_on_formula": 1
		},
		{
			"salary_component": "HRA - Payment Days",
			"abbr": "P_HRA",
			"type": "Earning",
			"depends_on_payment_days": 1,
			"amount_based_on_formula": 1,
			"formula": "base * 0.20"
		}
	]

	make_salary_component(earnings, False, company_list=["_Test Company"])

	deductions = [
		{
			"salary_component": "P - Professional Tax",
			"abbr": "P_PT",
			"type": "Deduction",
			"depends_on_payment_days": 1,
			"amount": 200.00
		},
		{
			"salary_component": "P - Employee Provident Fund",
			"abbr": "P_EPF",
			"type": "Deduction",
			"exempted_from_income_tax": 1,
			"amount_based_on_formula": 1,
			"depends_on_payment_days": 0,
			"formula": "(gross_pay - P_HRA) * 0.12"
		}
	]

	make_salary_component(deductions, False, company_list=["_Test Company"])

	salary_structure = "Salary Structure with PF"
	if frappe.db.exists("Salary Structure", salary_structure):
		frappe.db.delete("Salary Structure", salary_structure)

	details = {
		"doctype": "Salary Structure",
		"name": salary_structure,
		"company": "_Test Company",
		"payroll_frequency": "Monthly",
		"payment_account": get_random("Account", filters={"account_currency": "INR"}),
		"currency": "INR"
	}

	salary_structure_doc = frappe.get_doc(details)

	for entry in earnings:
		salary_structure_doc.append("earnings", entry)

	for entry in deductions:
		salary_structure_doc.append("deductions", entry)

	salary_structure_doc.insert()
	salary_structure_doc.submit()

	return salary_structure_doc

def make_salary_slip_for_payment_days_dependency_test(employee, salary_structure):
	employee = frappe.db.get_value(
		"Employee",
		{"user_id": employee},
		["name", "company", "employee_name"],
		as_dict=True
	)

	salary_slip_name = frappe.db.get_value("Salary Slip", {"employee": employee.name})

	if not salary_slip_name:
		salary_slip = make_salary_slip(salary_structure, employee=employee.name)
		salary_slip.employee_name = employee.employee_name
		salary_slip.payroll_frequency = "Monthly"
		salary_slip.posting_date = nowdate()
		salary_slip.insert()
	else:
		salary_slip = frappe.get_doc("Salary Slip", salary_slip_name)

	return salary_slip
