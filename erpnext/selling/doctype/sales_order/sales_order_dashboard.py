import frappe
from frappe import _

def get_data():
	reference_list = ['Quotation', 'Auto Repeat']
	if 'Vehicles' in frappe.get_active_domains():
		reference_list.append('Vehicle')

	return {
		'fieldname': 'sales_order',
		'non_standard_fieldnames': {
			'Journal Entry': 'reference_name',
			'Payment Entry': 'reference_name',
			'Payment Request': 'reference_name',
			'Auto Repeat': 'reference_document',
		},
		'internal_links': {
			'Quotation': ['items', 'quotation']
		},
		'transactions': [
			{
				'label': _('Fulfillment'),
				'items': ['Delivery Note', 'Sales Invoice', 'Pick List']
			},
			{
				'label': _('Reference'),
				'items': reference_list
			},
			{
				'label': _('Procurement'),
				'items': ['Material Request', 'Purchase Order', 'Work Order']
			},
			{
				'label': _('Payment'),
				'items': ['Payment Entry', 'Payment Request', 'Journal Entry']
			},
		]
	}