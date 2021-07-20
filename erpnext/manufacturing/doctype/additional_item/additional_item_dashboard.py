from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'add_additional_item',
		'transactions': [
			{
				'label': _('Material'),
				'items': ['Add Alternate Item']
			},
		]
	}