from frappe import _

def get_data():
	return {
		'fieldname': 'landed_cost_voucher',
		'non_standard_fieldnames': {
			'Journal Entry': 'reference_name',
			'Payment Entry': 'reference_name'
		},
		'transactions': [
			{
				'label': _('Payment'),
				'items': ['Payment Entry', 'Journal Entry']
			},
		]
	}