# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import datetime
import unittest

import frappe

from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.payroll.doctype.salary_slip.test_salary_slip import (
	make_deduction_salary_component,
	make_earning_salary_component,
	make_employee_salary_slip,
)
from erpnext.setup.setup_wizard.operations.install_fixtures import create_bank_account


class TestSalaryInformationFile(unittest.TestCase):
	def setUp(self):
		frappe.db.sql("""delete from tabBank""")
		frappe.db.sql("""delete from `tabHoliday List`""")
		create_holiday_list()

	def test_csv_generation_for_qatar_region(self):
		company = create_company("Qatar Financial", "QF", "Qatar")
		employee = make_employee("test_employee@qatar.com", company=company.name)
		doc = frappe.get_doc("Employee", employee)
		doc.holiday_list = "Holiday 2021"
		doc.save()
		set_data_for_employee(employee, "Qatar")

		make_earning_salary_component(setup=True, test_tax=True, company_list=[company.name])
		make_deduction_salary_component(setup=True, test_tax=True, company_list=[company.name])
		set_data_for_salary_component("Qatar")

		make_employee_salary_slip("test_employee@qatar.com", "Monthly")
		setup_bank_and_bank_account("Qatar Bank", "QIB", company.name)

	def test_csv_generation_for_uae_region(self):
		company = create_company("UAE Financial", "UF", "United Arab Emirates")
		employee = make_employee("test_employee@uae.com", company=company.name)
		doc = frappe.get_doc("Employee", employee)
		doc.holiday_list = "Holiday 2021"
		doc.save()
		set_data_for_employee(employee, "United Arab Emirates")

		make_earning_salary_component(setup=True, test_tax=True, company_list=[company.name])
		make_deduction_salary_component(setup=True, test_tax=True, company_list=[company.name])
		set_data_for_salary_component("United Arab Emirates")

		make_employee_salary_slip("test_employee@qatar.com", "Monthly")
		setup_bank_and_bank_account("UAE Bank", "UIB", company.name)

		create_salary_information_file(company)

def create_company(name, abbr, country):
	if frappe.db.exists("Company", name):
		return frappe.get_doc("Company", name)
	else:
		company = frappe.new_doc("Company")
		company.company_name = name
		company.abbr = abbr
		company.country = country
		company.default_currency = "AED"
		company.employer_establishment_id = "3456991283"
		if country == "United Arab Emirates":
			company.employer_reference_number = "78903564748"
		company.save()
	return company

def create_salary_information_file(company):
	sif = frappe.new_doc("Salary Information File")
	sif.company = company
	date = frappe.utils.get_datetime()
	sif.month = date.month
	sif.year = date.year

def set_data_for_employee(employee, country):
	employee = frappe.get_doc("Employee", employee)
	employee.residential_id = "123457890"
	employee.salary_mode = "Cash"
	employee.bank = "Qatar International"
	employee.bank_abbr = "QIB"
	employee.bank_ac_no = "9876543210"

	if country == "United Arab Emirates":
		employee.agent_id = "567891234"

	employee.save()

def set_data_for_salary_component(country):
	if country == "Qatar":
		frappe.db.set_value("Salary Component", "Basic Salary", "is_basic", 1)
	if country == "United Arab Emirates":
		frappe.db.set_value("Salary Component", "Basic Salary", "is_fixed_component", 1)
		frappe.db.set_value("Salary Component", "Performance Bonus", "is_variable_component", 1)

def setup_bank_and_bank_account(bank_name, abbr, company):
	bank = create_bank(bank_name, abbr)
	account = create_bank_account({"company_name": company, "bank_account": "WPS Account"})
	create_company_bank_account(account, bank, company)

def create_bank(bank_name, abbr):
	bank = frappe.db.exists("Bank", bank_name)
	if bank:
		return bank
	else:
		bank = frappe.new_doc("Bank")
		bank.bank_name = bank_name
		bank.swift_number = "2132932983"
		bank.bank_short_name = abbr
		bank.save()
		return bank.name

def create_company_bank_account(account, bank, company):
	bank_account = frappe.new_doc("Bank Account")
	bank_account.company = company
	bank_account.is_company_account = 1
	bank_account.account_name = "WPS Bank Account"
	bank_account.account = account.name
	bank_account.bank = bank
	bank_account.iban = "AT483200000012345864"
	bank_account.bank_code = "53276382839"
	bank_account.bank_account_no = "1234567891012"

	bank_account.save()

def create_holiday_list():
	doc = frappe.new_doc("Holiday List")
	doc.holiday_list_name = "Holiday 2021"
	doc.from_date = datetime.date(2021, 1, 1)
	doc.to_date = datetime.date(2021, 12, 31)
	doc.save()
