from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
		'fieldname': 'tax_category',
		'non_standard_fieldnames': {
			'Payment Entry': 'party_name'
		},
		'internal_links': {
			'Purchase Order': ['items', 'purchase_order'],
			'Project': ['items', 'project'],
			'Quality Inspection': ['items', 'quality_inspection'],
		},
		'transactions': [
			{
				'label': _('Pre Sales'),
				'items': ['Quotation', 'Supplier Quotation']
			},
			{
				'label': _('Sales'),
				'items': ['Sales Invoice', 'Delivery Note', 'Sales Order']
			},
			{
				'label': _('Purchase'),
				'items': ['Purchase Invoice', 'Purchase Receipt']
			},
			{
				'label': _('Party'),
				'items': ['Customer', 'Supplier']
			},
			{
				'label': _('Taxes'),
				'items': ['Item', 'Tax Rule']
			}
		]
	}
