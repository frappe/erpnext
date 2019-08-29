# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	''' Move credit limit and bypass credit limit to the child table of customer credit limit '''
	frappe.reload_doc("Selling", "doctype", "Customer Credit Limit")
	frappe.reload_doc("Selling", "doctype", "Customer")

	if frappe.db.a_row_exists("Customer Credit Limit"):
		return

	move_credit_limit_to_child_table()

def move_credit_limit_to_child_table():
	''' maps data from old field to the new field in the child table '''

	credit_limit_data = frappe.db.sql(''' SELECT
		name, credit_limit,
		bypass_credit_limit_check_against_sales_order
		FROM `tabCustomer`''', as_dict=1)

	default_company = frappe.db.get_single_value("Global Defaults", "default_company")

	for customer in credit_limit_data:
		customer = frappe.get_doc("Customer", customer.name)
		customer.append("credit_limit", {
			'credit_limit': customer.credit_limit,
			'bypass_credit_limit_check': customer.bypass_credit_limit_check_against_sales_order,
			'company': default_company
		})
		customer.save()