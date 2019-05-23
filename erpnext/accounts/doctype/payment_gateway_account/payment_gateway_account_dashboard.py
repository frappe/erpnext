from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
		'fieldname': 'payment_gateway_account',
		'non_standard_fieldnames': {
			'Subscription Plan': 'payment_gateway'
		},
		'transactions': [
			{
				'label': _('Payments'),
				'items': ['Payment Request']
			},
			{
				'label': _('Subscription Plans'),
				'items': ['Subscription Plan']
			}
		]
	}
