from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'prevdoc_docname',
		'non_standard_fieldnames': {
			'Payment Entry': 'reference_name'
		},
		'transactions': [
			{
				'items': ['Payment Entry']
			},
		]
	}