from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		# 'heatmap': True,
		# 'heatmap_message': _('PMS Calendar Extension Record'),
		'fieldname': 'name',
		'transactions': [
			{
				'label': _('Extension'),
				'items': ['PMS Extension']
			}
        ]
	}
