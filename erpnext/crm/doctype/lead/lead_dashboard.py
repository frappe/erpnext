from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'lead',
		'non_standard_fieldnames': {
			'Quotation': 'party_name',
			'Opportunity': 'party_name'
		},
		'dynamic_links': {
			'party_name': ['Lead', 'quotation_to']
		},
		'transactions': [
			{
				'items': ['Opportunity', 'Quotation']
			},
		]
	}