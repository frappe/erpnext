from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
		'fieldname': 'c_form',
		'non_standard_fieldnames': {
			'Sales Invoice': 'c_form_no'
		},
		'transactions': [
			{
				'label': _('Sales Invoice'),
				'items': ['Sales Invoice']
			}
		]
	}
