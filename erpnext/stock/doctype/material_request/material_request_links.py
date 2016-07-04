from frappe import _

links = {
	'fieldname': 'material_request',
	'non_standard_fieldnames': {
		'Purchase Order': 'prevdoc_detail_docname',
	},
	'transactions': [
		{
			'label': _('Related Documents'),
			'items': ['Request for Quotation', 'Supplier Quotation', 'Purchase Order']
		},
	]
}