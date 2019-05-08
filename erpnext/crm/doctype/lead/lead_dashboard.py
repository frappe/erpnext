from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'lead',
		'non_standard_fieldnames': {
			'Quotation': 'party_name',
			'Opportunity': 'party_name'
		},
		'transactions': [
			{
				'items': ['Opportunity', 'Quotation']
			},
		]
	}