import frappe
from frappe import _

def get_data():
	vehicle_gate_pass = []
	if 'Vehicles' in frappe.get_active_domains():
		vehicle_gate_pass = ['Vehicle Gate Pass']

	return {
		'fieldname': 'sales_invoice',
		'non_standard_fieldnames': {
			'Delivery Note': 'sales_invoice',
			'Journal Entry': 'reference_name',
			'Payment Entry': 'reference_name',
			'Payment Request': 'reference_name',
			'Sales Invoice': 'return_against',
			'Auto Repeat': 'reference_document',
		},
		'internal_links': {
			'Sales Order': ['items', 'sales_order'],
			'Delivery Note': ['items', 'delivery_note'],
			'Quotation': ['items', 'quotation'],
			'Vehicle': ['items', 'vehicle']
		},
		'transactions': [
			{
				'label': _('Payment'),
				'items': ['Payment Entry', 'Payment Request', 'Journal Entry']
			},
			{
				'label': _('Reference'),
				'items': ['Delivery Note', 'Sales Order', 'Quotation']
			},
			{
				'label': _('Reference'),
				'items': vehicle_gate_pass + ['Timesheet', 'Auto Repeat']
			},
			{
				'label': _('Returns'),
				'items': ['Sales Invoice']
			},
		]
	}
