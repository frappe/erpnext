from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'heatmap': True,
		'heatmap_message': _('This is based on the Time Sheets created against this project'),
		'fieldname': 'project',
		'transactions': [
			{
				'label': _('Project'),
				'items': ['Task', 'Issue', 'Project Update']
			},
			{
				'label': _('Material'),
				'items': ['Material Request', 'BOM', 'Stock Entry']
			},
			{
				'label': _('Work Done'),
				'items': ['Timesheet', 'Maintenance Visit', 'Quality Inspection']
			},
			{
				'label': _('Expenses'),
				'items': ['Employee Advance', 'Expense Claim', 'Landed Cost Voucher']
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
				'label': _('Payment'),
				'items': ['Payment Entry', 'Journal Entry']
			},
			{
				'label': _('Reference'),
				'items': ['Warranty Claim']
			},
		]
	}
