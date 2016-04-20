from frappe import _

links = {
	'fieldname': 'project',
	'transactions': [
		{
			'label': _('Project'),
			'items': ['Task', 'Time Log', 'Expense Claim', 'Issue']
		},
		{
			'label': _('Material'),
			'items': ['Material Request', 'BOM', 'Stock Entry']
		},
		{
			'label': _('Sales'),
			'items': ['Sales Order', 'Delivery Note', 'Sales Invoice']
		},
		{
			'label': _('Purchase'),
			'items': ['Purchase Order', 'Purchase Receipt', 'Purchase Invoice']
		},
	]
}
