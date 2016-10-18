from frappe import _

def get_data():
	return {
		'docstatus': 1,
		'fieldname': 'request_for_quotation',
		'transactions': [
			{
				'label': _('Related'),
				'items': ['Supplier Quotation']
			},
		]
	}