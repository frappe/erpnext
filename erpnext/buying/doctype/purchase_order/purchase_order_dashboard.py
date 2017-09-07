from frappe import _

def get_data():
	return {
		'fieldname': 'purchase_order',
		'non_standard_fieldnames': {
			'Journal Entry': 'reference_name',
			'Payment Entry': 'reference_name',
			'Subscription': 'reference_document'
		},
		'internal_links': {
			'Material Request': ['items', 'material_request'],
			'Supplier Quotation': ['items', 'supplier_quotation'],
			'Project': ['items', 'project'],
		},
		'transactions': [
			{
				'label': _('Related'),
				'items': ['Purchase Receipt', 'Purchase Invoice']
			},
			{
				'label': _('Payment'),
				'items': ['Payment Entry', 'Journal Entry']
			},
			{
				'label': _('Reference'),
				'items': ['Material Request', 'Supplier Quotation', 'Project', 'Subscription']
			},
			{
				'label': _('Sub-contracting'),
				'items': ['Stock Entry']
			},
		]
	}
