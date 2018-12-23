# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals
import unittest
import erpnext
import frappe
from dateutil.relativedelta import relativedelta
from erpnext.accounting.utils import get_fiscal_year, getdate, nowdate
from erpnext.hr.doctype.payroll_entry.payroll_entry import get_start_end_dates, get_end_date
from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.doctype.salary_slip.test_salary_slip import get_salary_component_account, \
		make_earning_salary_component, make_deduction_salary_component
from erpnext.hr.doctype.salary_structure.test_salary_structure import make_salary_structure
from erpnext.hr.doctype.loan.test_loan import create_loan

class TestPayrollEntry(unittest.TestCase):
	def setUp(self):
		for dt in ["Salary Slip", "Salary Component", "Salary Component Account", "Payroll Entry", "Loan"]:
			frappe.db.sql("delete from `tab%s`" % dt)

		make_earning_salary_component(setup=True)
		make_deduction_salary_component(setup=True)

	def test_payroll_entry(self): # pylint: disable=no-self-use
		company = erpnext.get_default_company()
		for data in frappe.get_all('Salary Component', fields = ["name"]):
			if not frappe.db.get_value('Salary Component Account',
				{'parent': data.name, 'company': company}, 'name'):
				get_salary_component_account(data.name)

		employee = frappe.db.get_value("Employee", {'company': company})
		make_salary_structure("_Test Salary Structure", "Monthly", employee)
		dates = get_start_end_dates('Monthly', nowdate())
		if not frappe.db.get_value("Salary Slip", {"start_date": dates.start_date, "end_date": dates.end_date}):
			make_payroll_entry(start_date=dates.start_date, end_date=dates.end_date)

	def test_get_end_date(self):
		self.assertEqual(get_end_date('2017-01-01', 'monthly'), {'end_date': '2017-01-31'})
		self.assertEqual(get_end_date('2017-02-01', 'monthly'), {'end_date': '2017-02-28'})
		self.assertEqual(get_end_date('2017-02-01', 'fortnightly'), {'end_date': '2017-02-14'})
		self.assertEqual(get_end_date('2017-02-01', 'bimonthly'), {'end_date': ''})
		self.assertEqual(get_end_date('2017-01-01', 'bimonthly'), {'end_date': ''})
		self.assertEqual(get_end_date('2020-02-15', 'bimonthly'), {'end_date': ''})
		self.assertEqual(get_end_date('2017-02-15', 'monthly'), {'end_date': '2017-03-14'})
		self.assertEqual(get_end_date('2017-02-15', 'daily'), {'end_date': '2017-02-15'})

	def test_loan(self):

		branch = "Test Employee Branch"
		applicant = make_employee("test_employee@loan.com")
		company = erpnext.get_default_company()
		holiday_list = make_holiday("test holiday for loan")

		company_doc = frappe.get_doc('Company', company)
		if not company_doc.default_payroll_payable_account:
			company_doc.default_payroll_payable_account = frappe.db.get_value('Account',
				{'company': company, 'root_type': 'Liability', 'account_type': ''}, 'name')
			company_doc.save()

		if not frappe.db.exists('Branch', branch):
			frappe.get_doc({
				'doctype': 'Branch',
				'branch': branch
			}).insert()

		employee_doc = frappe.get_doc('Employee', applicant)
		employee_doc.branch = branch
		employee_doc.holiday_list = holiday_list
		employee_doc.save()

		loan = create_loan(applicant,
			"Personal Loan", 280000, "Repay Over Number of Periods", 20)
		loan.repay_from_salary = 1
		loan.submit()
		salary_structure = "Test Salary Structure for Loan"
		make_salary_structure(salary_structure, "Monthly", employee_doc.name)

		dates = get_start_end_dates('Monthly', nowdate())
		make_payroll_entry(start_date=dates.start_date,
			end_date=dates.end_date, branch=branch)

		name = frappe.db.get_value('Salary Slip',
			{'posting_date': nowdate(), 'employee': applicant}, 'name')

		salary_slip = frappe.get_doc('Salary Slip', name)
		for row in salary_slip.loans:
			if row.loan == loan.name:
				interest_amount = (280000 * 8.4)/(12*100)
				principal_amount = loan.monthly_repayment_amount - interest_amount
				self.assertEqual(row.interest_amount, interest_amount)
				self.assertEqual(row.principal_amount, principal_amount)
				self.assertEqual(row.total_payment,
					interest_amount + principal_amount)

		if salary_slip.docstatus == 0:
			frappe.delete_doc('Salary Slip', name)


def make_payroll_entry(**args):
	args = frappe._dict(args)

	payroll_entry = frappe.new_doc("Payroll Entry")
	payroll_entry.company = args.company or erpnext.get_default_company()
	payroll_entry.start_date = args.start_date or "2016-11-01"
	payroll_entry.end_date = args.end_date or "2016-11-30"
	payroll_entry.payment_account = get_payment_account()
	payroll_entry.posting_date = nowdate()
	payroll_entry.payroll_frequency = "Monthly"
	payroll_entry.branch = args.branch or None
	payroll_entry.save()
	payroll_entry.create_salary_slips()
	payroll_entry.submit_salary_slips()
	if payroll_entry.get_sal_slip_list(ss_status = 1):
		payroll_entry.make_payment_entry()

	return payroll_entry

def get_payment_account():
	return frappe.get_value('Account',
		{'account_type': 'Cash', 'company': erpnext.get_default_company(),'is_group':0}, "name")

def make_holiday(holiday_list_name):
	if not frappe.db.exists('Holiday List', holiday_list_name):
		current_fiscal_year = get_fiscal_year(nowdate(), as_dict=True)
		dt = getdate(nowdate())

		new_year = dt + relativedelta(month=1, day=1, year=dt.year)
		republic_day = dt + relativedelta(month=1, day=26, year=dt.year)
		test_holiday = dt + relativedelta(month=2, day=2, year=dt.year)

		frappe.get_doc({
			'doctype': 'Holiday List',
			'from_date': current_fiscal_year.year_start_date,
			'to_date': current_fiscal_year.year_end_date,
			'holiday_list_name': holiday_list_name,
			'holidays': [{
				'holiday_date': new_year,
				'description': 'New Year'
			}, {
				'holiday_date': republic_day,
				'description': 'Republic Day'
			}, {
				'holiday_date': test_holiday,
				'description': 'Test Holiday'
			}]
		}).insert()

	return holiday_list_name
