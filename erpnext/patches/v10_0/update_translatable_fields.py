#-*- coding: utf-8 -*-

from __future__ import unicode_literals

import frappe

def execute():
	'''
	Enable translatable in these fields
	- Customer Name
	- Supplier Name
	- Contact Name
	- Item Name/ Description
	- Address
	'''

	frappe.reload_doc('core', 'doctype', 'docfield')
	frappe.reload_doc('custom', 'doctype', 'custom_field')

	enable_for_fields = [
		['Customer', 'customer_name'],
		['Supplier', 'supplier_name'],
		['Contact', 'first_name'],
		['Contact', 'last_name'],
		['Item', 'item_name'],
		['Item', 'description'],
		['Address', 'address_line1'],
		['Address', 'address_line2'],
	]


	for f in enable_for_fields:
		frappe.get_doc({
			'doctype': 'Property Setter',
			'doc_type': f[0],
			'doctype_or_field': 'DocField',
			'field_name': f[1],
			'property': 'translatable',
			'propery_type': 'Check',
			'value': 1
		}).db_insert()
