from frappe import _

def get_data():
	return {
		'fieldname': 'purchase_invoice',
		'non_standard_fieldnames': {
			'Journal Entry': 'reference_name',
			'Payment Entry': 'reference_name',
			'Payment Request': 'reference_name'
		},
		'transactions': [
			{
				'label': _('Payment'),
				'items': ['Payment Entry', 'Payment Request', 'Journal Entry']
			},
		]
	}