from frappe import _

data = {
	'docstatus': 1,
	'fieldname': 'purchase_order',
	'transactions': [
		{
			'label': _('Related Documents'),
			'items': ['Purchase Receipt', 'Purchase Invoice', 'Stock Entry']
		},
	]
}