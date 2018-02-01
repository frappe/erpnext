# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
import erpnext
from frappe.utils.make_random import get_random
from frappe.utils import nowdate, add_days, add_years, getdate, add_months
from erpnext.hr.doctype.salary_structure.salary_structure import make_salary_slip
from erpnext.hr.doctype.salary_slip.test_salary_slip \
	import make_earning_salary_component, make_deduction_salary_component

test_dependencies = ["Fiscal Year"]

class TestSalaryStructure(unittest.TestCase):
	def setUp(self):
		self.make_holiday_list()
		frappe.db.set_value("Company", erpnext.get_default_company(), "default_holiday_list", "Salary Structure Test Holiday List")
		make_employee("test_employee@salary.com")
		make_employee("test_employee_2@salary.com")

	def make_holiday_list(self):
		if not frappe.db.get_value("Holiday List", "Salary Structure Test Holiday List"):
			holiday_list = frappe.get_doc({
				"doctype": "Holiday List",
				"holiday_list_name": "Salary Structure Test Holiday List",
				"from_date": nowdate(),
				"to_date": add_years(nowdate(), 1),
				"weekly_off": "Sunday"
			}).insert()	
			holiday_list.get_weekly_off_dates()
			holiday_list.save()

	def test_amount_totals(self):
		sal_slip = frappe.get_value("Salary Slip", {"employee_name":"test_employee@salary.com"})
		if not sal_slip:
			sal_slip = make_salary_slip_from_salary_structure(employee=frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}))
			self.assertEquals(sal_slip.get("salary_structure"), 'Salary Structure Sample')
			self.assertEquals(sal_slip.get("earnings")[0].amount, 5000)
			self.assertEquals(sal_slip.get("deductions")[0].amount, 5000)
			self.assertEquals(sal_slip.get("deductions")[1].amount, 2500)
			self.assertEquals(sal_slip.get("total_deduction"), 7500)
			self.assertEquals(sal_slip.get("net_pay"), 7500)

	def test_whitespaces_in_formula_conditions_fields(self):
		make_salary_structure("Salary Structure Sample")
		salary_structure = frappe.get_doc("Salary Structure", "Salary Structure Sample")

		for row in salary_structure.earnings:
			row.formula = "\n%s\n\n"%row.formula
			row.condition = "\n%s\n\n"%row.condition

		for row in salary_structure.deductions:
			row.formula = "\n%s\n\n"%row.formula
			row.condition = "\n%s\n\n"%row.condition

		salary_structure.save()

		for row in salary_structure.earnings:
			self.assertFalse("\n" in row.formula or "\n" in row.condition)

		for row in salary_structure.deductions:
			self.assertFalse(("\n" in row.formula) or ("\n" in row.condition))

def make_employee(user):
	if not frappe.db.get_value("User", user):
		frappe.get_doc({
			"doctype": "User",
			"email": user,
			"first_name": user,
			"new_password": "password",
			"roles": [{"doctype": "Has Role", "role": "Employee"}]
		}).insert()

	if not frappe.db.get_value("Employee", {"user_id": user}):
		emp = frappe.get_doc({
			"doctype": "Employee",
			"naming_series": "EMP-",
			"employee_name": user,
			"company": erpnext.get_default_company(),
			"user_id": user,
			"date_of_birth": "1990-05-08",
			"date_of_joining": "2013-01-01",
			"relieving_date": "",
			"department": frappe.get_all("Department", fields="name")[0].name,
			"gender": "Female",
			"company_email": user,
			"status": "Active",
			"employment_type": "Intern"
		}).insert()
		return emp.name
	else:
		return frappe.get_value("Employee", {"employee_name":user}, "name")			

def make_salary_slip_from_salary_structure(employee):
	sal_struct = make_salary_structure('Salary Structure Sample')
	sal_slip = make_salary_slip(sal_struct, employee = employee)
	sal_slip.employee_name = frappe.get_value("Employee", {"name":employee}, "employee_name")
	sal_slip.start_date = nowdate()
	sal_slip.posting_date = nowdate()
	sal_slip.payroll_frequency =  "Monthly"
	sal_slip.insert()
	sal_slip.submit()
	return sal_slip	

def make_salary_structure(sal_struct, employees=None):
	if not frappe.db.exists('Salary Structure', sal_struct):
		frappe.get_doc({
			"doctype": "Salary Structure",
			"name": sal_struct,
			"company": erpnext.get_default_company(),
			"employees": employees or get_employee_details(),
			"earnings": get_earnings_component(),
			"deductions": get_deductions_component(),
			"payroll_frequency": "Monthly",
			"payment_account": frappe.get_value('Account', {'account_type': 'Cash', 'company': erpnext.get_default_company(),'is_group':0}, "name")
		}).insert()
	return sal_struct	

def get_employee_details():
	return [{"employee": frappe.get_value("Employee", {"employee_name":"test_employee@salary.com"}, "name"),
			"base": 25000,
			"variable": 5000,
			"from_date": add_months(nowdate(),-1),
			"idx": 1
			},
			{"employee": frappe.get_value("Employee", {"employee_name":"test_employee_2@salary.com"}, "name"),
			 "base": 15000,
			 "variable": 100,
			 "from_date": add_months(nowdate(),-1),
			 "idx": 2
			}
		]

def get_earnings_component():
	make_earning_salary_component(["Basic Salary", "Special Allowance", "HRA"])
	make_deduction_salary_component(["Professional Tax", "TDS"])

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
					"amount": 10000,
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
					"formula": 'base*.2',
					"idx": 1
				},
				{
					"salary_component": 'TDS',
					"abbr":'T',
					"condition": 'employment_type!="Intern"',
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
