# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import update_company_monthly_sales

def execute():
	'''Update company monthly sales field based on sales invoices this month'''
	companies = [d['name'] for d in frappe.get_list("Company")]

	for company in companies:
		update_company_monthly_sales(company)
