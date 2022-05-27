# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, floor, flt, get_datetime, get_first_day, getdate

from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.doctype.expense_claim.test_expense_claim import get_payable_account
from erpnext.hr.doctype.holiday_list.test_holiday_list import set_holiday_list
from erpnext.payroll.doctype.gratuity.gratuity import get_last_salary_slip
from erpnext.payroll.doctype.salary_slip.test_salary_slip import (
	make_deduction_salary_component,
	make_earning_salary_component,
	make_employee_salary_slip,
	make_holiday_list,
)
from erpnext.payroll.doctype.salary_structure.salary_structure import make_salary_slip
from erpnext.regional.united_arab_emirates.setup import create_gratuity_rule

test_dependencies = ["Salary Component", "Salary Slip", "Account"]


class TestGratuity(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Gratuity")
		frappe.db.delete("Salary Slip")
		frappe.db.delete("Additional Salary", {"ref_doctype": "Gratuity"})

		make_earning_salary_component(
			setup=True, test_tax=True, company_list=["_Test Company"], include_flexi_benefits=True
		)
		make_deduction_salary_component(setup=True, test_tax=True, company_list=["_Test Company"])
		make_holiday_list()

	@set_holiday_list("Salary Slip Test Holiday List", "_Test Company")
	def test_get_last_salary_slip_should_return_none_for_new_employee(self):
		new_employee = make_employee("new_employee@salary.com", company="_Test Company")
		salary_slip = get_last_salary_slip(new_employee)
		self.assertIsNone(salary_slip)

	@set_holiday_list("Salary Slip Test Holiday List", "_Test Company")
	def test_gratuity_based_on_current_slab_via_additional_salary(self):
		"""
		Range	|	Fraction
		5-0		|	1
		"""
		doj = add_days(getdate(), -(6 * 365))
		relieving_date = getdate()

		employee = make_employee(
			"test_employee_gratuity@salary.com",
			company="_Test Company",
			date_of_joining=doj,
			relieving_date=relieving_date,
		)
		sal_slip = create_salary_slip("test_employee_gratuity@salary.com")

		rule = get_gratuity_rule("Rule Under Unlimited Contract on termination (UAE)")

		gratuity = create_gratuity(pay_via_salary_slip=1, employee=employee, rule=rule.name)

		# work experience calculation
		employee_total_workings_days = (get_datetime(relieving_date) - get_datetime(doj)).days
		experience = floor(employee_total_workings_days / rule.total_working_days_per_year)
		self.assertEqual(gratuity.current_work_experience, experience)

		# amount calculation
		component_amount = frappe.get_all(
			"Salary Detail",
			filters={
				"docstatus": 1,
				"parent": sal_slip,
				"parentfield": "earnings",
				"salary_component": "Basic Salary",
			},
			fields=["amount"],
			limit=1,
		)
		gratuity_amount = component_amount[0].amount * experience
		self.assertEqual(flt(gratuity_amount, 2), flt(gratuity.amount, 2))

		# additional salary creation (Pay via salary slip)
		self.assertTrue(frappe.db.exists("Additional Salary", {"ref_docname": gratuity.name}))

		# gratuity should be marked "Paid" on the next salary slip submission
		salary_slip = make_salary_slip("Test Gratuity", employee=employee)
		salary_slip.posting_date = getdate()
		salary_slip.insert()
		salary_slip.submit()

		gratuity.reload()
		self.assertEqual(gratuity.status, "Paid")

	@set_holiday_list("Salary Slip Test Holiday List", "_Test Company")
	def test_gratuity_based_on_all_previous_slabs_via_payment_entry(self):
		"""
		Range	|	Fraction
		0-1		|	0
		1-5		|	0.7
		5-0		|	1
		"""
		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

		doj = add_days(getdate(), -(6 * 365))
		relieving_date = getdate()

		employee = make_employee(
			"test_employee_gratuity@salary.com",
			company="_Test Company",
			date_of_joining=doj,
			relieving_date=relieving_date,
		)

		sal_slip = create_salary_slip("test_employee_gratuity@salary.com")
		rule = get_gratuity_rule("Rule Under Limited Contract (UAE)")
		set_mode_of_payment_account()

		gratuity = create_gratuity(
			expense_account="Payment Account - _TC", mode_of_payment="Cash", employee=employee
		)

		# work experience calculation
		employee_total_workings_days = (get_datetime(relieving_date) - get_datetime(doj)).days
		experience = floor(employee_total_workings_days / rule.total_working_days_per_year)
		self.assertEqual(gratuity.current_work_experience, experience)

		# amount calculation
		component_amount = frappe.get_all(
			"Salary Detail",
			filters={
				"docstatus": 1,
				"parent": sal_slip,
				"parentfield": "earnings",
				"salary_component": "Basic Salary",
			},
			fields=["amount"],
			limit=1,
		)

		gratuity_amount = ((0 * 1) + (4 * 0.7) + (1 * 1)) * component_amount[0].amount
		self.assertEqual(flt(gratuity_amount, 2), flt(gratuity.amount, 2))
		self.assertEqual(gratuity.status, "Unpaid")

		pe = get_payment_entry("Gratuity", gratuity.name)
		pe.reference_no = "123467"
		pe.reference_date = getdate()
		pe.submit()

		gratuity.reload()
		self.assertEqual(gratuity.status, "Paid")
		self.assertEqual(flt(gratuity.paid_amount, 2), flt(gratuity.amount, 2))


def get_gratuity_rule(name):
	rule = frappe.db.exists("Gratuity Rule", name)
	if not rule:
		create_gratuity_rule()
	rule = frappe.get_doc("Gratuity Rule", name)
	rule.applicable_earnings_component = []
	rule.append("applicable_earnings_component", {"salary_component": "Basic Salary"})
	rule.save()

	return rule


def create_gratuity(**args):
	if args:
		args = frappe._dict(args)
	gratuity = frappe.new_doc("Gratuity")
	gratuity.employee = args.employee
	gratuity.posting_date = getdate()
	gratuity.gratuity_rule = args.rule or "Rule Under Limited Contract (UAE)"
	gratuity.pay_via_salary_slip = args.pay_via_salary_slip or 0
	if gratuity.pay_via_salary_slip:
		gratuity.payroll_date = getdate()
		gratuity.salary_component = "Performance Bonus"
	else:
		gratuity.expense_account = args.expense_account or "Payment Account - _TC"
		gratuity.payable_account = args.payable_account or get_payable_account("_Test Company")
		gratuity.mode_of_payment = args.mode_of_payment or "Cash"

	gratuity.save()
	gratuity.submit()

	return gratuity


def set_mode_of_payment_account():
	if not frappe.db.exists("Account", "Payment Account - _TC"):
		mode_of_payment = create_account()

	mode_of_payment = frappe.get_doc("Mode of Payment", "Cash")

	mode_of_payment.accounts = []
	mode_of_payment.append(
		"accounts", {"company": "_Test Company", "default_account": "_Test Bank - _TC"}
	)
	mode_of_payment.save()


def create_account():
	return frappe.get_doc(
		{
			"doctype": "Account",
			"company": "_Test Company",
			"account_name": "Payment Account",
			"root_type": "Asset",
			"report_type": "Balance Sheet",
			"currency": "INR",
			"parent_account": "Bank Accounts - _TC",
			"account_type": "Bank",
		}
	).insert(ignore_permissions=True)


def create_salary_slip(employee):
	if not frappe.db.exists("Salary Slip", {"employee": employee}):
		posting_date = get_first_day(add_months(getdate(), -1))
		salary_slip = make_employee_salary_slip(
			employee, "Monthly", "Test Gratuity", posting_date=posting_date
		)
		salary_slip.start_date = posting_date
		salary_slip.end_date = None
		salary_slip.submit()
		salary_slip = salary_slip.name
	else:
		salary_slip = get_last_salary_slip(employee)

	return salary_slip
