from frappe import _

def get_data():
	return {
		'fieldname': 'quotation',
		'non_standard_fieldnames': {
			'Auto Repeat': 'reference_document',
		},
		'transactions': [
			{
				'label': _('Order'),
				'items': ['Sales Order']
			},
			{
				'label': _('Delivery'),
				'items': ['Delivery Note']
			},
			{
				'label': _('Billing'),
				'items': ['Sales Invoice']
			},
			{
				'label': _('Subscription'),
				'items': ['Auto Repeat']
			},
		]
	}
