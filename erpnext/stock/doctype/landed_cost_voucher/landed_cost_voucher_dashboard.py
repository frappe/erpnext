from frappe import _

def get_data():
	return {
		'fieldname': 'landed_cost_voucher',
		'non_standard_fieldnames': {
			'Journal Entry': 'reference_name',
			'Payment Entry': 'reference_name'
		},
		'internal_links': {
			'Purchase Order': ['items', 'purchase_order'],
			'Purchase Receipt': ['items', 'purchase_receipt'],
			'Purchase Invoice': ['items', 'purchase_invoice'],
		},
		'transactions': [
			{
				'label': _('Payment'),
				'items': ['Payment Entry', 'Journal Entry']
			},
			{
				'label': _('Reference'),
				'items': ['Purchase Order', 'Purchase Receipt', 'Purchase Invoice']
			},
		]
	}