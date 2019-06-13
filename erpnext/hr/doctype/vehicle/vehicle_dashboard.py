from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'heatmap': True,
		'heatmap_message': _('This is based on logs against this Vehicle. See timeline below for details'),
		'fieldname': 'license_plate',
		'non_standard_fieldnames':{
			'Delivery Trip': 'vehicle'
		},
		'transactions': [
			{
				'items': ['Vehicle Log']
			},
			{
				'items': ['Delivery Trip']
			}
		]
	}