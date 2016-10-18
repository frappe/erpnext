from frappe import _

def get_data():
	return {
		'fieldname': 'purchase_order',
		'internal_links': {
			'Material Request': ['items', 'material_request'],
			'Supplier Quotation': ['items', 'supplier_quotation'],
			'Project': ['project'],
		},
		'transactions': [
			{
				'label': _('Related'),
				'items': ['Purchase Receipt', 'Purchase Invoice']
			},
			{
				'label': _('Reference'),
				'items': ['Material Request', 'Supplier Quotation', 'Project']
			},
			{
				'label': _('Sub-contracting'),
				'items': ['Stock Entry']
			},
		]
	}