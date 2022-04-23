from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
		'fieldname': 'shipping_rule',
		'non_standard_fieldnames': {
			'Payment Entry': 'party_name'
		},
		'transactions': [
			{
				'label': _('Pre Sales'),
				'items': ['Quotation', 'Supplier Quotation']
			},
			{
				'label': _('Sales'),
				'items': ['Sales Order', 'Delivery Note', 'Sales Invoice']
			},
			{
				'label': _('Purchase'),
				'items': ['Purchase Invoice', 'Purchase Order', 'Purchase Receipt']
			}
		]
	}
