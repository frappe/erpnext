from __future__ import unicode_literals
import frappe
from frappe import _

def get_data():
	procurement_list = ['Material Request', 'Purchase Order', 'Work Order']
	if 'Vehicles' in frappe.get_active_domains():
		procurement_list.append('Vehicle')

	return {
		'fieldname': 'sales_order',
		'non_standard_fieldnames': {
			'Delivery Note': 'against_sales_order',
			'Journal Entry': 'reference_name',
			'Payment Entry': 'reference_name',
			'Payment Request': 'reference_name',
			'Auto Repeat': 'reference_document',
		},
		'internal_links': {
			'Quotation': ['items', 'prevdoc_docname']
		},
		'transactions': [
			{
				'label': _('Fulfillment'),
				'items': ['Delivery Note', 'Sales Invoice', 'Pick List']
			},
			{
				'label': _('Procurement'),
				'items': procurement_list
			},
			{
				'label': _('Reference'),
				'items': ['Quotation', 'Project', 'Auto Repeat']
			},
			{
				'label': _('Payment'),
				'items': ['Payment Entry', 'Payment Request', 'Journal Entry']
			},
		]
	}