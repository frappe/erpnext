from frappe import _

def get_data():
	return {
		'fieldname': 'reference_name',
		'non_standard_fieldnames': {
			'Salary Slip': 'journal_entry',
		},
		'transactions': [
			{
				'label': _('Referenced By (Payment)'),
				'items': ['Journal Entry', 'Payment Entry']
			},
			{
				'label': _('Referenced By (Payroll)'),
				'items': ['Salary Slip']
			}
		]
	}