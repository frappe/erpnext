from frappe import _

def get_data():
	return {
		'fieldname': 'promotional_scheme',
		'transactions': [
			{
				'label': _('Reference'),
				'items': ['Pricing Rule']
			}
		]
	}