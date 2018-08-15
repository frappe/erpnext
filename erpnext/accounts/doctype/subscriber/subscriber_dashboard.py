from frappe import _

def get_data():
	return {
		'heatmap': True,
		'heatmap_message': _('This is based on transactions against this Subscriber. See timeline below for details'),
		'fieldname': 'subscriber',
		'transactions': [
			{
				'label': _('Subscriptions'),
				'items': ['Subscription']
			}
		]
	}