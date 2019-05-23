from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
		'fieldname': 'journal_entry',
		'non_standard_fieldnames': {
			'Stock Entry': 'credit_note',
		},
		'transactions': [
			{
				'label': _('Assets'),
				'items': ['Asset', 'Asset Value Adjustment']
			},
			{
				'label': _('Stock'),
				'items': ['Stock Entry']
			},
			{
				'label': _('Salaries'),
				'items': ['Salary Slip']
			}
		]
	}
