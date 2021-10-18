# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import os
import json
from frappe.permissions import add_permission, update_permission_property
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def setup(company=None, patch=True):
	# Company independent fixtures should be called only once at the first company setup
	if frappe.db.count('Company', {'country': 'United States'}) <=1:
		setup_company_independent_fixtures(patch=patch)

def setup_company_independent_fixtures(company=None, patch=True):
	make_custom_fields()
	add_print_formats()

def make_custom_fields(update=True):
	custom_fields = {
		'Supplier': [
			dict(fieldname='irs_1099', fieldtype='Check', insert_after='tax_id',
				label='Is IRS 1099 reporting required for supplier?')
		],
		'Sales Order': [
			dict(fieldname='exempt_from_sales_tax', fieldtype='Check', insert_after='taxes_and_charges',
				label='Is customer exempted from sales tax?')
		],
		'Sales Invoice': [
			dict(fieldname='exempt_from_sales_tax', fieldtype='Check', insert_after='taxes_section',
				label='Is customer exempted from sales tax?')
		],
		'Customer': [
			dict(fieldname='exempt_from_sales_tax', fieldtype='Check', insert_after='represents_company',
				label='Is customer exempted from sales tax?')
		],
		'Quotation': [
			dict(fieldname='exempt_from_sales_tax', fieldtype='Check', insert_after='taxes_and_charges',
				label='Is customer exempted from sales tax?')
		]
	}
	create_custom_fields(custom_fields, update=update)

def add_print_formats():
	frappe.reload_doc("regional", "print_format", "irs_1099_form")
	frappe.db.set_value("Print Format", "IRS 1099 Form", "disabled", 0)
