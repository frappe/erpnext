from frappe import _

def get_data():
	return {
		'fieldname': 'delivery_note',
		'non_standard_fieldnames': {
			'Stock Entry': 'delivery_note_no',
			'Quality Inspection': 'reference_name'
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