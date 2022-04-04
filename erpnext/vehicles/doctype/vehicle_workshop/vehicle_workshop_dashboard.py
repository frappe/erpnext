from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'vehicle_workshop',
		'transactions': [
			{
				'label': _('Repair Order'),
				'items': ['Project']
			},
			{
				'label': _('Vehicle Movement'),
				'items': ['Vehicle Service Receipt', 'Vehicle Gate Pass']
			},
		]
	}
