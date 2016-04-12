from frappe import _

links = {
	'fieldname': 'item_code',
	'non_standard_fieldnames': {
		'Production Order': 'production_item',
		'Product Bundle': 'new_item_code'
	},
	'transactions': [
		{
			'label': _('Related'),
			'items': ['BOM', 'Product Bundle', 'Serial No', 'Batch']
		},
		{
			'label': _('Pricing'),
			'items': ['Item Price', 'Pricing Rule']
		},
		{
			'label': _('Sell'),
			'items': ['Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice']
		},
		{
			'label': _('Buy'),
			'items': ['Material Request', 'Supplier Quotation', 'Request for Quotation',
				'Purchase Order', 'Purchase Invoice']
		},
		{
			'label': _('Move'),
			'items': ['Stock Entry']
		},
		{
			'label': _('Manufacture'),
			'items': ['Production Order']
		}
	]
}