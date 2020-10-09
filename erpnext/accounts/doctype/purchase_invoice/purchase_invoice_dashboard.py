from __future__ import unicode_literals
import frappe
from frappe import _

def get_data():
	reference_list = ['Purchase Order', 'Purchase Receipt', 'Asset', 'Landed Cost Voucher']
	if 'Vehicles' in frappe.get_active_domains():
		reference_list.append('Vehicle')

	return {
		'fieldname': 'purchase_invoice',
		'non_standard_fieldnames': {
			'Journal Entry': 'reference_name',
			'Payment Entry': 'reference_name',
			'Payment Request': 'reference_name',
			'Landed Cost Voucher': 'receipt_document',
			'Purchase Invoice': 'return_against',
			'Auto Repeat': 'reference_document'
		},
		'internal_links': {
			'Purchase Order': ['items', 'purchase_order'],
			'Purchase Receipt': ['items', 'purchase_receipt'],
			'Vehicle': ['items', 'vehicle']
		},
		'transactions': [
			{
				'label': _('Payment'),
				'items': ['Payment Entry', 'Payment Request', 'Journal Entry', 'Expense Claim']
			},
			{
				'label': _('Reference'),
				'items': reference_list
			},
			{
				'label': _('Returns'),
				'items': ['Purchase Invoice']
			},
			{
				'label': _('Subscription'),
				'items': ['Auto Repeat']
			},
		]
	}
