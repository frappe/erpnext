# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json
import os

import frappe


@frappe.whitelist()
def setup_demo_data():
	create_demo_company()
	process_demo_data()
	make_transactions()


def create_demo_company():
	company = frappe.db.get_value("Company", {"docstatus": 0})
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


def process_demo_data():
	demo_doctypes = frappe.get_hooks("demo_doctypes") or []
	path = os.path.join(os.path.dirname(__file__), "demo_data")
	for doctype in demo_doctypes:
		with open(os.path.join(path, doctype + ".json"), "r") as f:
			data = f.read()
			if data:
				for item in json.loads(data):
					create_demo_record(item)


def create_demo_record(doctype):
	frappe.get_doc(doctype).insert(ignore_permissions=True)


def make_transactions():
	pass
