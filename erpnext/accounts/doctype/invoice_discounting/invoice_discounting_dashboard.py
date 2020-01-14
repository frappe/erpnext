from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'reference_name',
		'internal_links': {
			'Sales Invoice': ['invoices', 'sales_invoice']
		},
		'transactions': [
			{
				'label': _('Reference'),
				'items': ['Sales Invoice']
			},
			{
				'label': _('Payment'),
				'items': ['Payment Entry', 'Journal Entry']
			}
		]
	}