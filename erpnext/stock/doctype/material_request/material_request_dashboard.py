from frappe import _

data = {
	'docstatus': 1,
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