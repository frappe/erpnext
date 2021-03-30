from __future__ import unicode_literals
from frappe import _


def get_data():
	return {
		'fieldname': 'material_request',
		'internal_links': {
			'Sales Order': ['items', 'sales_order'],
		},
		'transactions': [
			{
				'label': _('Purchase'),
				'items': ['Request for Quotation', 'Supplier Quotation', 'Purchase Order']
			},
			{
				'label': _('Stock'),
				'items': ['Stock Entry', 'Pick List']
			},
			{
				'label': _('Sales'),
				'items': ['Sales Order']
			},
			{
				'label': _('Manufacturing'),
				'items': ['Work Order']
			}
		]
	}