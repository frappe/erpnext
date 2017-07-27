from frappe import _

def get_data():
	return {
		'fieldname': 'supplier_quotation',
		'internal_links': {
			'Material Request': ['items', 'material_request'],
			'Request for Quotation': ['items', 'request_for_quotation'],
			'Project': ['items', 'project'],
		},
		'transactions': [
			{
				'label': _('Related'),
				'items': ['Purchase Order', 'Quotation']
			},
			{
				'label': _('Reference'),
				'items': ['Material Request', 'Request for Quotation', 'Project']
			},
		]

	}
