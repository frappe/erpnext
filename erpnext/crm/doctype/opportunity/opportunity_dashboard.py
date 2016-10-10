from frappe import _

data = {
	'fieldname': 'opportunity',
	'non_standard_fieldnames': {
		'Quotation': 'prevdoc_docname'
	},
	'transactions': [
		{
			'label': _('Related'),
			'items': ['Quotation', 'Supplier Quotation']
		},
	]
}