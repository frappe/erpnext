from frappe import _

def get_data():
	return {
		'fieldname': 'quality_inspection_template',
		'transactions': [
			{
				'label': _('Quality Inspection'),
				'items': ['Quality Inspection']
			}
		]
	}