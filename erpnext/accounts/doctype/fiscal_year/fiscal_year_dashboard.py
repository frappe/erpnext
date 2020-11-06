from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
		'fieldname': 'fiscal_year',
		'transactions': [
			{
				'label': _('Budgets'),
				'items': ['Budget']
			},
			{
				'label': _('References'),
				'items': ['Period Closing Voucher', 'Tax Withholding Category']
			},
			{
				'label': _('Target Details'),
				'items': ['Sales Person', 'Sales Partner', 'Territory', 'Monthly Distribution']
			}
		]
	}
