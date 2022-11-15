from frappe import _


def get_data():
	return {
		'fieldname': 'material_request',
		'internal_links': {
			'Sales Order': ['items', 'sales_order'],
		},
		'transactions': [
			{
				'label': _('Purchase'),
				'items': ['Purchase Order', 'Purchase Receipt']
			},
			{
				'label': _('Orders'),
				'items': ['Sales Order', 'Work Order']
			},
			{
				'label': _('Stock'),
				'items': ['Stock Entry', 'Pick List']
			},
			{
				'label': _('Pre Purchase'),
				'items': ['Request for Quotation', 'Supplier Quotation']
			},
		]
	}
