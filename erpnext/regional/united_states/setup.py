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
	add_product_tax_categories()
	make_custom_fields()
	add_permissions()
	frappe.enqueue('erpnext.regional.united_states.setup.add_product_tax_categories', now=False)
	add_print_formats()

# Product Tax categories imported from taxjar api
def add_product_tax_categories():
	with open(os.path.join(os.path.dirname(__file__), 'product_tax_category_data.json'), 'r') as f:
		tax_categories = json.loads(f.read())
	create_tax_categories(tax_categories['categories'])

def create_tax_categories(data):
	for d in data:
		tax_category = frappe.new_doc('Product Tax Category')
		tax_category.description = d.get("description")
		tax_category.product_tax_code = d.get("product_tax_code")
		tax_category.category_name = d.get("name")
		try:
			tax_category.db_insert()
		except frappe.DuplicateEntryError:
			pass


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
		],
		'Sales Invoice Item': [
			dict(fieldname='product_tax_category', fieldtype='Link', insert_after='description', options='Product Tax Category',
				label='Product Tax Category', fetch_from='item_code.product_tax_category'),
			dict(fieldname='tax_collectable', fieldtype='Currency', insert_after='net_amount',
				label='Tax Collectable', read_only=1),
			dict(fieldname='taxable_amount', fieldtype='Currency', insert_after='tax_collectable',
				label='Taxable Amount', read_only=1)
		],
		'Item': [
			dict(fieldname='product_tax_category', fieldtype='Link', insert_after='item_group', options='Product Tax Category',
				label='Product Tax Category')
		]
	}
	create_custom_fields(custom_fields, update=update)

def add_permissions():
	doctype = "Product Tax Category"
	for role in ('Accounts Manager', 'Accounts User', 'System Manager','Item Manager', 'Stock Manager'):
		add_permission(doctype, role, 0)
		update_permission_property(doctype, role, 0, 'write', 1)
		update_permission_property(doctype, role, 0, 'create', 1)

def add_print_formats():
	frappe.reload_doc("regional", "print_format", "irs_1099_form")
	frappe.db.set_value("Print Format", "IRS 1099 Form", "disabled", 0)
