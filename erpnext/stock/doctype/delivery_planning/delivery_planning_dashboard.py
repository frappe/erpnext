from __future__ import unicode_literals
from frappe import _

def get_data():
	return {

		'fieldname': 'related_delivery_planning',
		'non_standard_fieldnames': {
			'Batch': 'item'
		},
		'transactions': [
			{
				'label': _('Fulfillment'),
				'items': ['Pick List','Delivery Note']
			},
			{
				'label': _('Purchasing'),
				'items': ['Purchase Order']
			}
		]
	}
