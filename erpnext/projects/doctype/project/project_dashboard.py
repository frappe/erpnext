from frappe import _

def get_data():
	return {
		'heatmap': False,
		'heatmap_message': _('This is based on the Time Sheets created against this project'),
		'fieldname': 'project',
		'transactions': [
			{
				'label': _('Vehicle'),
				'items': ['Vehicle Service Receipt', 'Vehicle Gate Pass', 'Vehicle Log']
			},
			{
				'label': _('Sales'),
				'items': ['Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice']
			},
			{
				'label': _('Purchase'),
				'items': ['Supplier Quotation', 'Purchase Order', 'Purchase Receipt', 'Purchase Invoice']
			},
			{
				'label': _('Tasks'),
				'items': ['Task', 'Issue', 'Project Update']
			},
			{
				'label': _('Work Done'),
				'items': ['Timesheet', 'Maintenance Visit', 'Quality Inspection']
			},
			{
				'label': _('Material'),
				'items': ['Stock Entry', 'Material Request', 'BOM']
			},
			{
				'label': _('Expenses'),
				'items': ['Employee Advance', 'Expense Claim', 'Landed Cost Voucher']
			},
			{
				'label': _('Accounting'),
				'items': ['Journal Entry', 'Payment Entry']
			},
		]
	}
