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

	fields=""
	if frappe.db.has_column('Customer', 'bypass_credit_limit_check_at_sales_order'):
		fields = ", bypass_credit_limit_check_at_sales_order"

	credit_limit_record = frappe.db.sql(''' SELECT
			name, credit_limit
			{0}
		FROM `tabCustomer`'''.format(fields), as_dict=1) #nosec

	companies = frappe.get_all("Company", 'name')

	for record in credit_limit_record:
		customer = frappe.get_doc("Customer", customer.name)
		for company in companies:
			customer.append("credit_limit_reference", {
				'credit_limit': record.credit_limit,
				'bypass_credit_limit_check': record.bypass_credit_limit_check_at_sales_order,
				'company': company.name
			})
		customer.save()