from __future__ import unicode_literals

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from erpnext.erpnext_integrations.doctype.taxjar_settings.taxjar_settings import add_permissions


def execute():
	company = frappe.get_all('Company', filters = {'country': 'United States'}, fields=['name'])
	if not company:
		return

	TAXJAR_CREATE_TRANSACTIONS = frappe.db.get_single_value("TaxJar Settings", "taxjar_create_transactions")
	TAXJAR_CALCULATE_TAX = frappe.db.get_single_value("TaxJar Settings", "taxjar_calculate_tax")
	TAXJAR_SANDBOX_MODE = frappe.db.get_single_value("TaxJar Settings", "is_sandbox")

	if (not TAXJAR_CREATE_TRANSACTIONS and not TAXJAR_CALCULATE_TAX and not TAXJAR_SANDBOX_MODE):
		return

	custom_fields = {
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
	create_custom_fields(custom_fields, update=True)
	add_permissions()
	frappe.enqueue('erpnext.erpnext_integrations.doctype.taxjar_settings.taxjar_settings.add_product_tax_categories', now=True)
