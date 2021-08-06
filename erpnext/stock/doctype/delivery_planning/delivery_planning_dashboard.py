from __future__ import unicode_literals
from frappe import _

def get_data():
	return {

		'fieldname': 'related_delivery_planning',
		'non_standard_fieldnames': {
			'Delivery Planning Item' : 'related_delivey_planning',
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
			},
			# {
			# 	'label': _('Planning'),
			# 	'items': ['Delivery Planning Item']
			# }
		]
	}
