from frappe import _


def get_data():
	return {
		'fieldname': 'material_request',
		'transactions': [
			{
				'label': _('Related'),
				'items': ['Request for Quotation', 'Supplier Quotation', 'Purchase Order']
			},
			{
				'label': _('Manufacturing'),
				'items': ['Production Order']
			}
		]
	}