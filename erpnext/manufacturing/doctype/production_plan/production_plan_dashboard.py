from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'production_plan',
		'transactions': [
			{
				'label': _('Related'),
				'items': ['Work Order', 'Material Request']
			},
		]
	}