from __future__ import unicode_literals
import frappe
from frappe import _

def get_data():
	reference_list = ['Sales Order', 'Quality Inspection']
	if 'Vehicles' in frappe.get_active_domains():
		reference_list.append('Vehicle')

	return {
		'fieldname': 'delivery_note',
		'non_standard_fieldnames': {
			'Stock Entry': 'delivery_note_no',
			'Quality Inspection': 'reference_name',
			'Auto Repeat': 'reference_document',
			'Delivery Note': 'return_against'
		},
		'internal_links': {
			'Sales Order': ['items', 'against_sales_order'],
			'Vehicle': ['items', 'vehicle']
		},
		'transactions': [
			{
				'label': _('Fulfilment'),
				'items': ['Sales Invoice', 'Packing Slip', 'Delivery Trip']
			},
			{
				'label': _('Reference'),
				'items': reference_list
			},
			{
				'label': _('Returns'),
				'items': ['Delivery Note']
			},
			{
				'label': _('Subscription'),
				'items': ['Auto Repeat']
			},
		]
	}