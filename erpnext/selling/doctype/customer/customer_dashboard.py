from frappe import _

def get_data():
	return {
		'heatmap': True,
		'heatmap_message': _('This is based on transactions against this Customer. See timeline below for details'),
		'fieldname': 'customer',
		'transactions': [
			{
				'label': _('Pre Sales'),
				'items': ['Opportunity', 'Quotation']
			},
			{
				'label': _('Orders'),
				'items': ['Sales Order', 'Delivery Note', 'Sales Invoice']
			},
			{
				'label': _('Support'),
				'items': ['Issue']
			},
			{
				'label': _('Projects'),
				'items': ['Project']
			}
		]
	}