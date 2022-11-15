from frappe import _

def get_data():
	return {
		'fieldname': 'warranty_claim',
		'non_standard_fieldnames': {
			'Maintenance Visit': 'prevdoc_docname',
		},
		'transactions': [
			{
				'label': _('Visit'),
				'items': ['Maintenance Visit']
			},
		]
	}
