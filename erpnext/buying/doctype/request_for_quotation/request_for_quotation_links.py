from frappe import _

links = {
	'fieldname': 'supplier_quotation',
	# 'non_standard_fieldnames': {
	# 	'Purchase Order': 'prevdoc_detail_docname',
	# },
	'transactions': [
		{
			'label': _('Related Documents'),
			'items': ['Supplier Quotation', 'Purchase Order']
		},
	]
}