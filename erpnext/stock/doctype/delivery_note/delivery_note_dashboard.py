from frappe import _

data = {
	'fieldname': 'delivery_note_no',
	'non_standard_fieldnames': {
		'Sales Invoice': 'delivery_note',
		'Packing Slip': 'delivery_note',
	},
	'internal_links': {
		'Sales Order': ['items', 'against_sales_order'],
	},
	'transactions': [
		{
			'label': _('Related'),
			'items': ['Sales Invoice', 'Packing Slip']
		},
		{
			'label': _('Reference'),
			'items': ['Sales Order', 'Quality Inspection']
		},
		{
			'label': _('Returns'),
			'items': ['Stock Entry']
		},
	]
}