from frappe import _

links = {
	'fieldname': 'request_for_quotation',
	# 'non_standard_fieldnames': {
	# 	'Purchase Order': 'prevdoc_detail_docname',
	# },
	'transactions': [
		{
			'label': _('Related Documents'),
			'items': ['Supplier Quotation']
		},
	]
}