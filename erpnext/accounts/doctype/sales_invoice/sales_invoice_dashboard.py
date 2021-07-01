from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'sales_invoice',
		'non_standard_fieldnames': {
			'Delivery Note': 'against_sales_invoice',
			'Journal Entry': 'reference_name',
			'Payment Entry': 'reference_name',
			'Payment Request': 'reference_name',
			'Sales Invoice': 'return_against',
			'Auto Repeat': 'reference_document',
			# 'Backorder': 'backorder_references',
			'Integration Request': 'reference_id_'
		},
		'internal_links': {
			'Sales Order': ['items', 'sales_order']
		},
		'transactions': [
			# {
			# 	'label': _('Payment'),
			# 	'items': ['Payment Entry', 'Payment Request', 'Journal Entry', 'Invoice Discounting']
			# },
			{
				'label': _('Payment'),
				'items': ['Payment Entry', 'Payment Request', 'Journal Entry']
			},
			# {
			# 	'label': _('Reference'),
			# 	'items': ['Timesheet', 'Delivery Note', 'Sales Order']
			# },
			{
				'label': _('Returns & WooCommerce Integration'),
				'items': ['Sales Invoice', 'Integration Request']
			},
			{
				'label': _('Testing'),
				'items': ['Sample']
			},
			{
				'label': 'Shipments',
				'items': ['Shipment Entry']
			},
			# {
			# 	'label': _('Subscription'),
			# 	'items': ['Auto Repeat']
			# },
		]
	}
