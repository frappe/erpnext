from frappe import _

def get_data():
	return {
		'fieldname': 'loan',
		'non_standard_fieldnames': {
			'Journal Entry': 'reference_name',
			'Loan Application': 'applicant'
		},
		'transactions': [
			{
				'label': _('Applicant'),
				'items': ['Loan Application']
			},
			{
				'label': _('Account'),
				'items': ['Journal Entry']
			},
			{
				'label': _('Employee'),
				'items': ['Salary Slip']
			}
		]
	}