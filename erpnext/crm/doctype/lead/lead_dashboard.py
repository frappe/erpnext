from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'lead',
		'non_standard_fieldnames': {
			'Quotation': 'customer_name',
			'Opportunity': 'customer_name'
		},
		'transactions': [
			{
				'items': ['Opportunity', 'Quotation']
			},
		]
	}