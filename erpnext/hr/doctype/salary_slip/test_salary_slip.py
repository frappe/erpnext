# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import unittest
import frappe
import erpnext
import calendar
import random
from erpnext.accounts.utils import get_fiscal_year
from frappe.utils.make_random import get_random
from frappe.utils import getdate, nowdate, add_days, add_months, flt, get_first_day, get_last_day, rounded
from erpnext.hr.doctype.salary_structure.salary_structure import make_salary_slip
from erpnext.hr.doctype.salary_structure.test_salary_structure import make_salary_structure
from erpnext.hr.doctype.payroll_entry.payroll_entry import get_month_details
from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.doctype.employee_tax_exemption_declaration.test_employee_tax_exemption_declaration import create_payroll_period, create_exemption_category
from erpnext.hr.doctype.leave_application.test_leave_application import make_leave_application

class TestSalarySlip(unittest.TestCase):
	def setUp(self):
		make_earning_salary_component(setup=True)
		make_deduction_salary_component(setup=True)

		for dt in ["Leave Application", "Leave Allocation", "Salary Slip", "Additional Salary"]:
			frappe.db.sql("delete from `tab%s`" % dt)

		make_holiday_list()

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

	def test_tax_for_payroll_period(self):
		data = {}
		# test the impact of tax exemption declaration, tax exemption proof submission and deduct check boxes in annual tax calculation
		# as per assigned salary structure 40500 in monthly salary so 236000*5/100/12
		frappe.db.sql("""delete from `tabPayroll Period`""")
		frappe.db.sql("""delete from `tabSalary Component`""")
		payroll_period = create_payroll_period()
		create_tax_slab(payroll_period)
		employee = make_employee("test_tax@salary.slip")
		delete_docs = ["Salary Slip", "Additional Salary",
						"Employee Tax Exemption Declaration",
						"Employee Tax Exemption Proof Submission",
						"Employee Benefit Claim", "Salary Structure Assignment"]
		for doc in delete_docs:
			frappe.db.sql("delete from `tab%s` where employee='%s'" % (doc, employee))

		from erpnext.hr.doctype.salary_structure.test_salary_structure import \
			make_salary_structure, create_salary_structure_assignment
		salary_structure = make_salary_structure("Stucture to test tax", "Monthly",
			other_details={"max_benefits": 100000}, test_tax=True)
		create_salary_structure_assignment(employee, salary_structure.name,
			payroll_period.start_date)

		# create salary slip for whole period deducting tax only on last period
		# to find the total tax amount paid
		create_salary_slips_for_payroll_period(employee, salary_structure.name,
			payroll_period, deduct_random=False)
		tax_paid = get_tax_paid_in_period(employee)

		# total taxable income 586000, 250000 @ 5%, 86000 @ 20% ie. 12500 + 17200
		annual_tax = 29700
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
		data["proof-1"] = create_proof_submission(employee, payroll_period, 50000)
		data["proof-2"] = create_proof_submission(employee, payroll_period, 70000)

		# Submit benefit claim for total 50000
		data["benefit-1"] = create_benefit_claim(employee, payroll_period, 15000, "Medical Allowance")
		data["benefit-2"] = create_benefit_claim(employee, payroll_period, 35000, "Leave Travel Allowance")


		frappe.db.sql("""delete from `tabSalary Slip` where employee=%s""", (employee))
		data["deducted_dates"] = create_salary_slips_for_payroll_period(employee,
			salary_structure.name, payroll_period)
		tax_paid = get_tax_paid_in_period(employee)

		# total taxable income 416000, 166000 @ 5% ie. 8300
		try:
			self.assertEqual(tax_paid, 8300)
		except AssertionError:
			print("\nSalary Slip - Tax calculation failed on following case\n", data, "\n")
			raise

		# create additional salary of 150000
		frappe.db.sql("""delete from `tabSalary Slip` where employee=%s""", (employee))
		data["additional-1"] = create_additional_salary(employee, payroll_period, 50000)
		data["additional-2"] = create_additional_salary(employee, payroll_period, 100000)
		data["deducted_dates"] = create_salary_slips_for_payroll_period(employee,
			salary_structure.name, payroll_period)

		# total taxable income 566000, 250000 @ 5%, 66000 @ 20%, 12500 + 13200
		tax_paid = get_tax_paid_in_period(employee)
		try:
			self.assertEqual(tax_paid, 25700)
		except AssertionError:
			print("\nSalary Slip - Tax calculation failed on following case\n", data, "\n")
			raise
		frappe.db.sql("""delete from `tabAdditional Salary` where employee=%s""", (employee))

	def test_component_prorated_based_on_attendance(self):
		from erpnext.hr.doctype.additional_salary.test_additional_salary \
			import create_salary_component_if_missing, create_additional_salary

		employee = make_employee("test_email@erpnext.org")
		salary_structure = make_salary_structure("Salary Structure Sample", "Monthly", employee)

		create_salary_component_if_missing(salary_component="Additional Allowance", prorated_based_on_attendance=1)
		create_additional_salary(salary_component="Additional Allowance", employee=employee)

		leave_application = make_leave_application(employee=employee, leave_type="_Test Leave Type Negative", allow_negative=1, include_holiday=1)

		salary_slip = make_salary_slip(salary_structure.name, employee=employee)

		self.assertEqual(salary_slip.total_leaves, 1)

		addl_comp = [d for d in salary_slip.earnings if d.salary_component=="Additional Allowance"]
		self.assertEqual(addl_comp[0].amount, rounded(100*(salary_slip.total_working_days - 1)/salary_slip.total_working_days))

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

def make_holiday_list():
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

def make_employee_salary_slip(user, payroll_frequency, salary_structure=None):
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

def make_salary_component(salary_components, test_tax):
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
		get_salary_component_account(salary_component["salary_component"])

def get_salary_component_account(sal_comp):
	company = erpnext.get_default_company()
	sal_comp = frappe.get_doc("Salary Component", sal_comp)
	if not sal_comp.get("accounts"):
		sal_comp.append("accounts", {
			"company": company,
			"default_account": create_account(company)
		})
		sal_comp.save()

def create_account(company):
	salary_account = frappe.db.get_value("Account", "Salary - " + frappe.get_cached_value('Company',  company,  'abbr'))
	if not salary_account:
		frappe.get_doc({
		"doctype": "Account",
		"account_name": "Salary",
		"parent_account": "Indirect Expenses - " + frappe.get_cached_value('Company',  company,  'abbr'),
		"company": company
		}).insert()
	return salary_account

def make_earning_salary_component(setup=False, test_tax=False):
	data = [
			{
				"salary_component": 'Basic Salary',
				"abbr":'BS',
				"condition": 'base > 10000',
				"formula": 'base*.5',
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
				"is_additional_component": 1,
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
							"max_benefit_amount": 100000
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
							"salary_component": "Perfomance Bonus",
							"abbr": 'B',
							"is_additional_component": 1,
							"type": "Earning"
						}
					])
	if setup or test_tax:
		make_salary_component(data, test_tax)
	data.append({
					"salary_component": 'Basic Salary',
					"abbr":'BS',
					"condition": 'base < 10000',
					"formula": 'base*.2',
					"type": "Earning",
					"amount_based_on_formula": 1
				})
	return data

def make_deduction_salary_component(setup=False, test_tax=False):
	data =  [
				{
					"salary_component": 'Professional Tax',
					"abbr":'PT',
					"condition": 'base > 10000',
					"formula": 'base*.1',
					"type": "Deduction",
					"amount_based_on_formula": 1
				},
				{
					"salary_component": 'TDS',
					"abbr":'T',
					"formula": 'base*.1',
					"type": "Deduction",
					"amount_based_on_formula": 1
				}
			]
	if not test_tax:
		data.append({
			"salary_component": 'TDS',
			"abbr":'T',
			"condition": 'employment_type=="Intern"',
			"formula": 'base*.1',
			"type": "Deduction",
			"amount_based_on_formula": 1
		})
	if setup or test_tax:
		make_salary_component(data, test_tax)

	return data

def get_tax_paid_in_period(employee):
	tax_paid_amount = frappe.db.sql("""select sum(sd.amount) from `tabSalary Detail`
		sd join `tabSalary Slip` ss where ss.name=sd.parent and ss.employee=%s
		and ss.docstatus=1 and sd.salary_component='TDS'""", (employee))
	return tax_paid_amount[0][0]

def create_exemption_declaration(employee, payroll_period):
	create_exemption_category()
	declaration = frappe.get_doc({"doctype": "Employee Tax Exemption Declaration",
									"employee": employee,
									"payroll_period": payroll_period,
									"company": erpnext.get_default_company()})
	declaration.append("declarations", {"exemption_sub_category": "_Test Sub Category",
							"exemption_category": "_Test Category",
							"amount": 100000})
	declaration.submit()

def create_proof_submission(employee, payroll_period, amount):
	submission_date = add_months(payroll_period.start_date, random.randint(0, 11))
	proof_submission = frappe.get_doc({"doctype": "Employee Tax Exemption Proof Submission",
									"employee": employee,
									"payroll_period": payroll_period.name,
									"submission_date": submission_date})
	proof_submission.append("tax_exemption_proofs", {"exemption_sub_category": "_Test Sub Category",
				"exemption_category": "_Test Category", "type_of_proof": "Test", "amount": amount})
	proof_submission.submit()
	return submission_date

def create_benefit_claim(employee, payroll_period, amount, component):
	claim_date = add_months(payroll_period.start_date, random.randint(0, 11))
	frappe.get_doc({"doctype": "Employee Benefit Claim", "employee": employee,
		"claimed_amount": amount, "claim_date": claim_date, "earning_component":
		component}).submit()
	return claim_date

def create_tax_slab(payroll_period):
	data = [{
				"from_amount": 250000,
				"to_amount": 500000,
				"percent_deduction": 5
			},
			{
				"from_amount": 500000,
				"to_amount": 1000000,
				"percent_deduction": 20
			},
			{
				"from_amount": 1000000,
				"percent_deduction": 30
			}]
	payroll_period.taxable_salary_slabs = []
	for item in data:
		payroll_period.append("taxable_salary_slabs", item)
	payroll_period.save()

def create_salary_slips_for_payroll_period(employee, salary_structure, payroll_period, deduct_random=True):
	deducted_dates = []
	i = 0
	while i < 12:
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
		"salary_component": "Perfomance Bonus",
		"from_date": salary_date,
		"to_date": salary_date,
		"amount": amount,
		"type": "Earning"}).submit()
	return salary_date
