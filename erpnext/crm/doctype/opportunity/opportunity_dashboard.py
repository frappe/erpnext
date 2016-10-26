from frappe import _

def get_data():
	return {
		'fieldname': 'prevdoc_docname',
		'transactions': [
			{
				'label': _('Related'),
				'items': ['Quotation', 'Supplier Quotation']
			},
		]
	}