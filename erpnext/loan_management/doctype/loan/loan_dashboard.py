from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'loan',
		'non_standard_fieldnames': {
			'Loan Disbursement': 'against_loan',
			'Loan Repayment': 'against_loan',
		},
		'transactions': [
			{
				'label': _('Pledges'),
				'items': ['Loan Security Pledge']
			},
			{
				'label': _('Shortfall'),
				'items': ['Loan Security Shortfall']
			},
			{
				'label': _('Disbursement'),
				'items': ['Loan Disbursement']
			},
			{
				'label': _('Repayments'),
				'items': ['Loan Repayment']
			},
			{
				'label': _('Interest Accrual'),
				'items': ['Loan Interest Accrual']
			}
		]
	}