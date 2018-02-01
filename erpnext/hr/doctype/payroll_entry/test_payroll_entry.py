# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals
import unittest
import erpnext
import frappe
from dateutil.relativedelta import relativedelta
from erpnext.accounts.utils import get_fiscal_year, getdate, nowdate
from erpnext.hr.doctype.payroll_entry.payroll_entry import get_start_end_dates, get_end_date

class TestPayrollEntry(unittest.TestCase):
	def test_payroll_entry(self): # pylint: disable=no-self-use

		for data in frappe.get_all('Salary Component', fields = ["name"]):
			if not frappe.db.get_value('Salary Component Account',
				{'parent': data.name, 'company': erpnext.get_default_company()}, 'name'):
				get_salary_component_account(data.name)

		if not frappe.db.get_value("Salary Slip", {"start_date": "2016-11-01", "end_date": "2016-11-30"}):
			make_payroll_entry()

	def test_get_end_date(self):
		self.assertEqual(get_end_date('2017-01-01', 'monthly'), {'end_date': '2017-01-31'})
		self.assertEqual(get_end_date('2017-02-01', 'monthly'), {'end_date': '2017-02-28'})
		self.assertEqual(get_end_date('2017-02-01', 'fortnightly'), {'end_date': '2017-02-14'})
		self.assertEqual(get_end_date('2017-02-01', 'bimonthly'), {'end_date': ''})
		self.assertEqual(get_end_date('2017-01-01', 'bimonthly'), {'end_date': ''})
		self.assertEqual(get_end_date('2020-02-15', 'bimonthly'), {'end_date': ''})
		self.assertEqual(get_end_date('2017-02-15', 'monthly'), {'end_date': '2017-03-14'})
		self.assertEqual(get_end_date('2017-02-15', 'daily'), {'end_date': '2017-02-15'})

	def test_employee_loan(self):
		from erpnext.hr.doctype.salary_structure.test_salary_structure import (make_employee,
			make_salary_structure)
		from erpnext.hr.doctype.employee_loan.test_employee_loan import create_employee_loan

		branch = "Test Employee Branch"
		employee = make_employee("test_employee@loan.com")
		company = erpnext.get_default_company()
		holiday_list = make_holiday("test holiday for loan")

		if not frappe.db.exists('Salary Component', 'Basic Salary'):
			frappe.get_doc({
				'doctype': 'Salary Component',
				'salary_component': 'Basic Salary',
				'salary_component_abbr': 'BS',
				'type': 'Earning',
				'accounts': [{
					'company': company,
					'default_account': frappe.db.get_value('Account',
						{'company': company, 'root_type': 'Expense', 'account_type': ''}, 'name')
				}]
			}).insert()

		if not frappe.db.get_value('Salary Component Account',
			{'parent': 'Basic Salary', 'company': company}):
			salary_component = frappe.get_doc('Salary Component', 'Basic Salary')
			salary_component.append('accounts', {
				'company': company,
				'default_account': 'Salary - WP'
			})

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

		employee_doc = frappe.get_doc('Employee', employee)
		employee_doc.branch = branch
		employee_doc.holiday_list = holiday_list
		employee_doc.save()

		employee_loan = create_employee_loan(employee,
			"Personal Loan", 280000, "Repay Over Number of Periods", 20)
		employee_loan.repay_from_salary = 1
		employee_loan.submit()

		salary_strcture = "Test Salary Structure for Loan"
		if not frappe.db.exists('Salary Structure', salary_strcture):
			salary_strcture = make_salary_structure(salary_strcture, [{
				'employee': employee,
				'from_date': '2017-01-01',
				'base': 30000
			}])

			salary_strcture = frappe.get_doc('Salary Structure', salary_strcture)
			salary_strcture.set('earnings', [{
				'salary_component': 'Basic Salary',
				'abbr': 'BS',
				'amount_based_on_formula':1,
				'formula': 'base*.5'
			}])
			salary_strcture.save()

		dates = get_start_end_dates('Monthly', nowdate())
		make_payroll_entry(start_date=dates.start_date,
			end_date=dates.end_date, branch=branch)

		name = frappe.db.get_value('Salary Slip',
			{'posting_date': nowdate(), 'employee': employee}, 'name')

		salary_slip = frappe.get_doc('Salary Slip', name)
		for row in salary_slip.loans:
			if row.employee_loan == employee_loan.name:
				interest_amount = (280000 * 8.4)/(12*100)
				principal_amount = employee_loan.monthly_repayment_amount - interest_amount
				self.assertEqual(row.interest_amount, interest_amount)
				self.assertEqual(row.principal_amount, principal_amount)
				self.assertEqual(row.total_payment,
					interest_amount + principal_amount)

		if salary_slip.docstatus == 0:
			frappe.delete_doc('Salary Slip', name)

		employee_loan.cancel()
		frappe.delete_doc('Employee Loan', employee_loan.name)

def get_salary_component_account(sal_comp):
	company = erpnext.get_default_company()
	sal_comp = frappe.get_doc("Salary Component", sal_comp)
	sc = sal_comp.append("accounts")
	sc.company = company
	sc.default_account = create_account(company)

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

def make_payroll_entry(**args):
	args = frappe._dict(args)

	payroll_entry = frappe.new_doc("Payroll Entry")
	payroll_entry.company = erpnext.get_default_company()
	payroll_entry.start_date = args.start_date or "2016-11-01"
	payroll_entry.end_date = args.end_date or "2016-11-30"
	payroll_entry.payment_account = get_payment_account()
	payroll_entry.posting_date = nowdate()
	payroll_entry.payroll_frequency = "Monthly"
	payroll_entry.branch = args.branch or None
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

		new_year = dt + relativedelta(month=01, day=01, year=dt.year)
		republic_day = dt + relativedelta(month=01, day=26, year=dt.year)
		test_holiday = dt + relativedelta(month=02, day=02, year=dt.year)

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
