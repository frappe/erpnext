from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
		'fieldname': 'payment_term',
		'transactions': [
			{
				'label': _('Invoices and Orders'),
				'items': ['Sales Invoice', 'Sales Order', 'Purchase Invoice', 'Purchase Order', 'Quotation']
			},
			{
				'label': _('Payment Terms Template'),
				'items': ['Payment Terms Template']
			}
		]
	}
