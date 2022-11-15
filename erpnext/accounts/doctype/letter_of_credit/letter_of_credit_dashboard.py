from frappe import _

def get_data():
	return {
		'fieldname': 'letter_of_credit',
		'non_standard_fieldnames': {
			'Payment Entry': 'party',
			'Journal Entry': 'party',
		},
		'transactions': [
			{
				'label': _('Payments and Vouchers'),
				'items': ['Journal Entry', 'Payment Entry']
			},
			{
				'label': _('Purchase'),
				'items': ['Purchase Receipt', 'Purchase Invoice']
			}
		]
	}
