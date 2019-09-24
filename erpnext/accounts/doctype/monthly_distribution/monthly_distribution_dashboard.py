from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
		'fieldname': 'monthly_distribution',
		'non_standard_fieldnames': {
			'Sales Person': 'distribution_id',
			'Territory': 'distribution_id',
			'Sales Partner': 'distribution_id',
		},
		'transactions': [
			{
				'label': _('Target Details'),
				'items': ['Sales Person', 'Territory', 'Sales Partner']
			},
			{
				'items': ['Budget']
			}
		]
	}