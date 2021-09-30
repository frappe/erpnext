# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import unittest

import frappe
from frappe.utils import add_to_date, getdate
from frappe.utils.make_random import get_random

from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.payroll.doctype.salary_structure.test_salary_structure import (
	create_salary_structure_assignment,
)
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

company = "_Test Company"
emp_name= "test_sales_commission@payout.com"
earning_component_data = [
	{
		"salary_component": 'Basic Salary',
		"abbr":'BS',
		"type": "Earning"
	},
	{
		"salary_component": 'HRA',
		"abbr":'H',
		"type": "Earning"
	},
]
sales_commission_component = [
	{
		"salary_component": 'Sales Commission',
		"abbr":'SC',
		"type": "Earning"
	},
]
deduction_component_data = [
	{
		"salary_component": 'Professional Tax',
		"abbr":'PT',
		"type": "Deduction",
		"exempted_from_income_tax": 1
	}
]
salary_structure = "Salary Structure for Sales Commission"

class TestSalesCommission(unittest.TestCase):
	def setUp(self):
		setup_test()

	def tearDown(self):
		for dt in ["Additional Salary", "Salary Structure Assignment", "Salary Structure"]:
			frappe.db.sql("delete from `tab%s`" % dt)

	def test_sales_commision_via_additional_salary(self):
		make_so(emp_name)
		sc = self.make_sc()

		sc.submit()
		sc.payout_entry()

		add_sal = frappe.get_all("Additional Salary", filters={"ref_docname": sc.name})
		for entry in add_sal:
			if frappe.get_value("Additional Salary", filters={"name": entry["name"]}, fieldname=["employee"]) == sc.employee:
				add_sal_doc = frappe.get_doc("Additional Salary", entry['name'])

				self.assertEqual(add_sal_doc.amount, sc.total_commission_amount)

	def test_sales_commision_via_payment_entry(self):
		make_so(emp_name)
		sc = self.make_sc(via_salary=0)

		sc.submit()
		sc.payout_entry(mode_of_payment="Cash")

		pe = frappe.get_all("Payment Entry Reference", filters={"reference_name": sc.name}, fields=["parent"])
		for entry in pe:
			if frappe.get_value("Payment Entry", filters={"name":entry["parent"]}, fieldname=["party"]) == sc.employee:
				pe_doc = frappe.get_doc("Payment Entry", entry["parent"])

				self.assertEqual(pe_doc.paid_amount, sc.total_commission_amount)

	def make_sc(self, via_salary=1):
		sc = frappe.new_doc("Sales Commission")
		sc.sales_person = "test_sales_commission@payout.com"
		sc.company = company
		sc.pay_via_salary = via_salary
		sc.commission_based_on = "Sales Order"
		sc.from_date = add_to_date(getdate(), days=-2)
		sc.to_date = getdate()
		sc.add_contributions()
		sc.insert()

		return sc

def setup_test():
	emp_id = make_employee(emp_name, company=company)
	make_sales_person(emp_id, emp_name)
	make_salary_component(earning_component_data)
	make_salary_component(sales_commission_component)
	make_salary_component(deduction_component_data)
	make_salary_structure(salary_structure)
	create_salary_structure_assignment(
		emp_id,
		salary_structure,
		company=company,
		currency="INR"
	)

	frappe.db.set_value("Payroll Settings", "Payroll Settings", "salary_component_for_sales_commission", sales_commission_component[0]["salary_component"])
	frappe.db.set_value("Selling Settings", "Selling Settings", "approval_required_for_sales_commission_payout", 0)
	frappe.db.sql("delete from `tabAdditional Salary`")
	frappe.db.set_value("Payroll Settings", None, "email_salary_slip_to_employee", 0)

def add_sales_person(so, emp):
	sales_person = {
		"sales_person": emp,
		"allocated_percentage": 100,
		"commission_rate":10
	}
	so.append("sales_team", sales_person)

def make_salary_structure(salary_structure):
	if frappe.db.exists("Salary Structure", salary_structure):
		frappe.db.delete("Salary Structure", salary_structure)

	details = {
		"doctype": "Salary Structure",
		"name": salary_structure,
		"company": company,
		"payroll_frequency": "Monthly",
		"payment_account": get_random("Account", filters={"account_currency": "INR"}),
		"currency": "INR"
	}

	salary_structure_doc = frappe.get_doc(details)

	for entry in earning_component_data:
		salary_structure_doc.append("earnings", entry)

	for entry in deduction_component_data:
		salary_structure_doc.append("deductions", entry)

	salary_structure_doc.insert()
	salary_structure_doc.submit()

def make_salary_component(salary_components):
	for salary_component in salary_components:
		if not frappe.db.exists('Salary Component', salary_component["salary_component"]):
			salary_component["doctype"] = "Salary Component"
			salary_component["salary_component_abbr"] = salary_component["abbr"]
			frappe.get_doc(salary_component).insert()
		get_salary_component_account(salary_component["salary_component"])

def get_salary_component_account(sal_comp):
	sal_comp = frappe.get_doc("Salary Component", sal_comp)
	if not sal_comp.get("accounts"):
		company_abbr = frappe.get_cached_value('Company', company, 'abbr')

		if sal_comp.type == "Earning":
			account_name = "Salary"
			parent_account = "Indirect Expenses - " + company_abbr
		else:
			account_name = "Salary Deductions"
			parent_account = "Current Liabilities - " + company_abbr

		sal_comp.append("accounts", {
			"company": company,
			"account": create_account(account_name, parent_account)
		})
		sal_comp.save()

def create_account(account_name, parent_account):
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

def make_sales_person(emp, emp_name):
	if frappe.db.exists("Sales Person", {"employee":emp}):
		frappe.db.set_value("Sales Person", "sales_person_name", emp_name)
	else:
		sales_person = frappe.new_doc("Sales Person")
		sales_person.sales_person_name = emp_name
		sales_person.employee = emp
		sales_person.insert()

def make_so(emp_name):
	so = make_sales_order(do_not_save=1)
	add_sales_person(so, emp_name)
	so.transaction_date = add_to_date(getdate(), days=-1)
	so.submit()

	return so