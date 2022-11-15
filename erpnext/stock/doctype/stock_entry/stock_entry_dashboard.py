import frappe
from frappe import _

def get_data():
	return {
		'fieldname': 'stock_entry',
		'internal_links': {
			'Material Request': ['items', 'material_request']
		},
		'transactions': [
			{
				'label': _('Reference'),
				'items': ['Material Request']
			},
		]
	}
