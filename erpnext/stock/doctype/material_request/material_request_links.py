from frappe import _

links = {
	'fieldname': 'material_request',
	'non_standard_fieldnames': {
		'Supplier Quotation': 'prevdoc_detail_docname',
		'Purchase Order': 'prevdoc_detail_docname',
	},
	'transactions': [
		{
			'label': _('Documents'),
			'items': ['Request for Quotation', 'Supplier Quotation', 'Purchase Order']
		},
	]
}