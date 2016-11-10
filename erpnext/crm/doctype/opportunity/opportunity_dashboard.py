from frappe import _

def get_data():
	return {
		'fieldname': 'prevdoc_docname',
		'non_standard_fieldnames': {
			'Supplier Quotation': 'opportunity',
		},
		'transactions': [
			{
				'label': _('Related'),
				'items': ['Quotation', 'Supplier Quotation']
			},
		]
	}