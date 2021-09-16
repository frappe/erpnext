from __future__ import unicode_literals

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from erpnext.regional.united_states.setup import add_permissions


def execute():
	company = frappe.get_all('Company', filters = {'country': 'United States'}, fields=['name'])
	if not company:
		return

	frappe.reload_doc("regional", "doctype", "product_tax_category")

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
	frappe.enqueue('erpnext.regional.united_states.setup.add_product_tax_categories', now=True)