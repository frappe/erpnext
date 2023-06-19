# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json
import os
from random import randint

import frappe
from frappe.utils import add_days

import erpnext


@frappe.whitelist()
def setup_demo_data():
	company = create_demo_company()
	process_masters()
	make_transactions(company)


@frappe.whitelist()
def clear_demo_data():
	company = frappe.db.get_single_value("Global Defaults", "demo_company")
	create_transaction_deletion_record(company)
	clear_masters()
	delete_company(company)


def create_demo_company():
	company = erpnext.get_default_company()
	company_doc = frappe.get_doc("Company", company)

	# Make a dummy company
	new_company = frappe.new_doc("Company")
	new_company.company_name = company_doc.company_name + " (Demo)"
	new_company.abbr = company_doc.abbr + "D"
	new_company.enable_perpetual_inventory = 1
	new_company.default_currency = company_doc.default_currency
	new_company.country = company_doc.country
	new_company.chart_of_accounts_based_on = "Standard Template"
	new_company.chart_of_accounts = company_doc.chart_of_accounts
	new_company.insert()

	# Set Demo Company as default to
	frappe.db.set_single_value("Global Defaults", "demo_company", new_company.name)
	frappe.db.set_default("company", new_company.name)

	return new_company.name


def process_masters():
	for doctype in frappe.get_hooks("demo_master_doctypes"):
		data = read_data_file_using_hooks(doctype)
		if data:
			for item in json.loads(data):
				create_demo_record(item)


def create_demo_record(doctype):
	frappe.get_doc(doctype).insert(ignore_permissions=True)


def make_transactions(company):
	fiscal_year = frappe.db.get_single_value("Global Defaults", "current_fiscal_year")
	start_date = frappe.db.get_value("Fiscal Year", fiscal_year, "year_start_date")

	for doctype in frappe.get_hooks("demo_transaction_doctypes"):
		data = read_data_file_using_hooks(doctype)
		if data:
			for item in json.loads(data):
				create_transaction(item, company, start_date)


def create_transaction(doctype, company, start_date):
	doctype.update(
		{
			"company": company,
			"set_posting_time": 1,
			"posting_date": get_random_date(start_date),
		}
	)

	income_account, expense_account = frappe.db.get_value(
		"Company", company, ["default_income_account", "default_expense_account"]
	)

	for item in doctype.get("items"):
		item.update(
			{
				"cost_center": erpnext.get_default_cost_center(company),
				"income_account": income_account,
				"expense_account": expense_account,
			}
		)

	doc = frappe.get_doc(doctype)
	doc.save(ignore_permissions=True)
	doc.submit()


def get_random_date(start_date):
	return add_days(start_date, randint(1, 365))


def create_transaction_deletion_record(company):
	transaction_deletion_record = frappe.new_doc("Transaction Deletion Record")
	transaction_deletion_record.company = company
	transaction_deletion_record.save(ignore_permissions=True)
	transaction_deletion_record.submit()


def clear_masters():
	for doctype in frappe.get_hooks("demo_master_doctypes")[::-1]:
		data = read_data_file_using_hooks(doctype)
		if data:
			for item in json.loads(data):
				clear_demo_record(item)


def clear_demo_record(doctype):
	doc_type = doctype.get("doctype")
	del doctype["doctype"]
	doc = frappe.get_doc(doc_type, doctype)
	frappe.delete_doc(doc.doctype, doc.name, ignore_permissions=True)


def delete_company(company):
	frappe.delete_doc("Company", company, ignore_permissions=True)


def read_data_file_using_hooks(doctype):
	path = os.path.join(os.path.dirname(__file__), "demo_data")
	with open(os.path.join(path, doctype + ".json"), "r") as f:
		data = f.read()

	return data
