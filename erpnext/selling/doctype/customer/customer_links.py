from frappe import _

links = {
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