from frappe import _


def get_data():
	return {
		'fieldname': 'subcontracting_order',
		'transactions': [
			{
				'label': _('Unknown'),
				'items': ['Subcontracting Receipt', 'Stock Entry']
			}
		]
	}
