# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.payroll.doctype.salary_slip.test_salary_slip import make_employee_salary_slip
from erpnext.payroll.doctype.gratuity.gratuity import get_last_salary_slip
from erpnext.regional.united_arab_emirates.setup import create_gratuity_rule
from frappe.utils import getdate, add_days, get_datetime, flt


class TestGratuity(unittest.TestCase):

	def setUp(self):
		frappe.db.sql("DELETE FROM `tabgratuity`")
		frappe.db.sql("DELETE FROM `tabAdditional Salary` WHERE ref_doctype = 'Gratuity'")


	def test_check_gratuity_amount_based_on_current_slab_and_additional_salary_creation(self):
		employee, sal_slip = create_employee_and_get_last_salary_slip()
		rule = frappe.db.exists("Gratuity Rule", "Rule Under Unlimited Contract on termination (UAE)")
		if not rule:
			create_gratuity_rule()
		else:
			rule = frappe.get_doc("Gratuity Rule", "Rule Under Unlimited Contract on termination (UAE)")
		rule.applicable_earnings_component = []
		rule.append("applicable_earnings_component", {
			"salary_component": "Basic Salary"
		})
		rule.save()
		rule.reload()

		gra = frappe.new_doc("Gratuity")
		gra.employee = employee
		gra.posting_date = getdate()
		gra.gratuity_rule = rule.name
		gra.pay_via_salary_slip = 1
		gra.salary_component = "Performance Bonus"
		gra.payroll_date = getdate()
		gra.save()
		gra.submit()

		#work experience calculation
		date_of_joining, relieving_date = frappe.db.get_value('Employee', employee, ['date_of_joining', 'relieving_date'])
		employee_total_workings_days = (get_datetime(relieving_date) - get_datetime(date_of_joining)).days

		experience = employee_total_workings_days/rule.total_working_days_per_year

		gra.reload()

		from math import floor

		self.assertEqual(floor(experience), gra.current_work_experience)

		#amount Calculation 6
		component_amount = frappe.get_list("Salary Detail",
		filters={
			"docstatus": 1,
			'parent': sal_slip,
			"parentfield": "earnings",
			'salary_component': "Basic Salary"
		},
		fields=["amount"])

		''' 5 - 0 fraction is 1 '''

		gratuity_amount = component_amount[0].amount * experience
		gra.reload()

		self.assertEqual(flt(gratuity_amount, 2), flt(gra.amount, 2))

		#additional salary creation (Pay via salary slip)
		self.assertTrue(frappe.db.exists("Additional Salary", {"ref_docname": gra.name}))
		self.assertEqual(gra.status, "Paid")



	def test_check_gratuity_amount_based_on_all_previous_slabs(self):
		employee, sal_slip = create_employee_and_get_last_salary_slip()
		rule = frappe.db.exists("Gratuity Rule", "Rule Under Limited Contract (UAE)")
		if not rule:
			create_gratuity_rule()
		else:
			rule = frappe.get_doc("Gratuity Rule", rule)
		rule.applicable_earnings_component = []
		rule = frappe.get_doc("Gratuity Rule", "Rule Under Limited Contract (UAE)")
		rule.append("applicable_earnings_component", {
			"salary_component": "Basic Salary"
		})
		rule.save()
		rule.reload()

		mof = frappe.get_doc("Mode of Payment", "Cheque")
		mof.accounts = []
		mof.append("accounts", {
			"company": "_Test Company",
			"default_account": "_Test Bank - _TC"
		})

		mof.save()

		gra = frappe.new_doc("Gratuity")
		gra.employee = employee
		gra.posting_date = getdate()
		gra.gratuity_rule = rule.name
		gra.pay_via_salary_slip = 0
		gra.payroll_date = getdate()
		gra.expense_account = "Payment Account - _TC"
		gra.mode_of_payment = "Cheque"

		gra.save()
		gra.submit()

		#work experience calculation
		date_of_joining, relieving_date = frappe.db.get_value('Employee', employee, ['date_of_joining', 'relieving_date'])
		employee_total_workings_days = (get_datetime(relieving_date) - get_datetime(date_of_joining)).days

		experience = employee_total_workings_days/rule.total_working_days_per_year

		gra.reload()

		from math import floor

		self.assertEqual(floor(experience), gra.current_work_experience)

		#amount Calculation 6
		component_amount = frappe.get_list("Salary Detail",
		filters={
			"docstatus": 1,
			'parent': sal_slip,
			"parentfield": "earnings",
			'salary_component': "Basic Salary"
		},
		fields=["amount"])


		''' range  | Fraction
			0-1    |    0
			1-5    |   0.7
			5-0    |    1
		'''


		gratuity_amount = ((0 * 1) + (4 * 0.7) + (1 * 1)) *  component_amount[0].amount
		gra.reload()

		self.assertEqual(flt(gratuity_amount, 2), flt(gra.amount, 2))
		self.assertEqual(gra.status, "Unpaid")


		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

		pay_entry = get_payment_entry("Gratuity", gra.name)
		pay_entry.reference_no = "123467"
		pay_entry.reference_date = getdate()

		pay_entry.save()
		pay_entry.submit()

		gra.reload()

		self.assertEqual(gra.status, "Paid")
		self.assertEqual(gra.paid_amount, flt(gra.amount, 2))

def create_employee_and_get_last_salary_slip():
	employee = make_employee("test_employee@salary.com")
	frappe.db.set_value("Employee", employee, "relieving_date", getdate())
	frappe.db.set_value("Employee", employee, "date_of_joining", add_days(getdate(), - (6*365)))
	if not frappe.db.exists("Salary Slip", {"employee":employee}):
		salary_slip = make_employee_salary_slip("test_employee@salary.com", "Monthly")
		salary_slip.submit()
		salary_slip = salary_slip.name
	else:
		salary_slip = get_last_salary_slip(employee)

	return employee, salary_slip

