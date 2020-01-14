from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'heatmap': True,
		'heatmap_message': _('Member Activity'),
		'fieldname': 'member',
		'transactions': [
			{
				'label': _('Membership Details'),
				'items': ['Membership']
			}
		]
	}