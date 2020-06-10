from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
		'fieldname': 'payment_term',
		'transactions': [
			{
				'label': _('Sales'),
				'items': ['Sales Invoice', 'Sales Order', 'Quotation']
			},
			{
				'label': _('Purchase'),
				'items': ['Purchase Invoice', 'Purchase Order']
			},
			{
				'items': ['Payment Terms Template']
			}
		]
	}
