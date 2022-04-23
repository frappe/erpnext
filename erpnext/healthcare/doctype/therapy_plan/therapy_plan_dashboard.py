from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'therapy_plan',
		'non_standard_fieldnames': {
			'Sales Invoice': 'reference_dn'
		},
		'transactions': [
			{
				'label': _('Therapy Sessions'),
				'items': ['Therapy Session']
			},
			{
				'label': _('Billing'),
				'items': ['Sales Invoice']
			}
		],
		'disable_create_buttons': ['Sales Invoice']
	}
