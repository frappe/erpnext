from frappe import _

def get_data():
	return {
		'fieldname': 'name',
		'non_standard_fieldnames': {
			'Sales Invoice': 'subscription_id',
		},
		'transactions': [
			{
				'label': _('Subscription Document'),
				'items': ['Sales Invoice']
			}
		]
	}