from frappe import _


def get_data():
	return {
		'fieldname': 'transaction_type',
		'transactions': [
			{
				'label': _('Configuration'),
				'items': ['Item Default Rule']
			}
		]
	}
