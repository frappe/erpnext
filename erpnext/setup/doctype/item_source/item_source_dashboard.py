from frappe import _


def get_data():
	return {
		'fieldname': 'item_source',
		'transactions': [
			{
				'label': _('Configuration'),
				'items': ['Item Default Rule']
			}
		]
	}
