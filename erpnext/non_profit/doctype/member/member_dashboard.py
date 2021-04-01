from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'heatmap': True,
		'heatmap_message': _('Member Activity'),
		'fieldname': 'member',
		'non_standard_fieldnames': {
			'Bank Account': 'party'
		},
		'transactions': [
			{
				'label': _('Membership Details'),
				'items': ['Membership']
			},
			{
				'label': _('Fee'),
				'items': ['Bank Account']
			}
		]
	}
