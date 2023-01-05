# import frappe
from frappe import _


def get_data():
	return {
		'fieldname': 'packing_slip',
		'internal_links': {
			'Sales Order': ['items', 'sales_order'],
		},
		'transactions': [
			{
				'label': _('Previous Documents'),
				'items': ['Sales Order']
			},
		]
	}
