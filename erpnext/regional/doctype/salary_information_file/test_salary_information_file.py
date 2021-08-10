# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from erpnext.payroll.doctype.salary_structure.salary_structure import make_salary_slip
import frappe
import unittest
from erpnext.accounts.doctype.period_closing_voucher.test_period_closing_voucher import create_company
from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.payroll.doctype.salary_slip.test_salary_slip import make_employee_salary_slip, make_earning_salary_component, make_deduction_salary_component
from erpnext.setup.setup_wizard.operations.install_fixtures import create_bank_account

class TestSalaryInformationFile(unittest.TestCase):
	def test_for_csv_genration_for_qatar_region():
		company = create_company("Qatar Financial", "QF", "Qatar")
		employee = make_employee("test_employee@qatar.com", company=company.name)
		set_data_for_employee(employee, "Qatar")
		employee.reload()

		make_earning_salary_component(setup=True, test_tax=True, company_list=[company.name])
		make_deduction_salary_component(setup=True, test_tax=True, company_list=[company.name])
		set_data_for_salary_component("Qatar")

		make_employee_salary_slip("test_employee@qatar.com", "Monthly")
		setup_bank_and_bank_account("Qatar Bank", "QIB", company.name)

	def test_for_csv_generation_for_uae_region():
		company = create_company("UAE Financial", "UF", "United Arab Emirates")
		employee = make_employee("test_employee@uae.com", company=company.name)
		set_data_for_employee(employee, "United Arab Emirates")
		employee.reload()

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
	sif.month =
	sif.year = date.year

def set_data_for_employee(employee, country):
	employee = frappe.get_doc("Employee", employee)
	employee.residential_id = "123457890"
	employee.salary_mode = "Salary"
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
	account = create_bank_account({"company_name": company, "bank_account": "WPS test bank"})
	company_bank_account = create_company_bank_account(account, bank, company)

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
	bank_account.is_bank_account = 1
	bank_account.account_name = "WPS bank"
	bank_account.account = account
	bank_account.bank = bank
	bank_account.iban = "AT483200000012345864"
	bank_account.bank_code = "53276382839"
	bank_account.bank_account_no = "788989778789"

	bank_account.save()


