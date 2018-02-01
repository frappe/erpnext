from frappe import _

def get_data():
	return {
		'heatmap': True,
		'heatmap_message': _('Memeber Activity'),
		'fieldname': 'member',
		'transactions': [
			{
				'label': _('Membership Details'),
				'items': ['Membership']
			}
		]
	}