# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.selling.doctype.customer.customer import update_customer_current_month_sales

def execute():
	'''Update customer monthly sales history based on sales invoices'''
	frappe.reload_doctype("Customer")
	customers = [d['name'] for d in frappe.get_list("Customer")]

	for customer in customers:
		update_customer_current_month_sales(customer)
