from __future__ import unicode_literals
import frappe
from frappe import _

def get_data():
	reference_list = ['Timesheet', 'Delivery Note', 'Sales Order']
	if 'Vehicles' in frappe.get_active_domains():
		reference_list.append('Vehicle')

	return {
		'fieldname': 'sales_invoice',
		'non_standard_fieldnames': {
			'Delivery Note': 'against_sales_invoice',
			'Journal Entry': 'reference_name',
			'Payment Entry': 'reference_name',
			'Payment Request': 'reference_name',
			'Sales Invoice': 'return_against',
			'Auto Repeat': 'reference_document',
		},
		'internal_links': {
			'Sales Order': ['items', 'sales_order'],
			'Delivery Note': ['items', 'delivery_note'],
			'Vehicle': ['items', 'vehicle']
		},
		'transactions': [
			{
				'label': _('Payment'),
				'items': ['Payment Entry', 'Payment Request', 'Journal Entry', 'Invoice Discounting']
			},
			{
				'label': _('Reference'),
				'items': reference_list
			},
			{
				'label': _('Returns'),
				'items': ['Sales Invoice']
			},
			{
				'label': _('Subscription'),
				'items': ['Auto Repeat']
			},
		]
	}
