from __future__ import unicode_literals
from frappe import _


def get_data():
	return {
		'fieldname': 'material_request',
		'transactions': [
			{
				'label': _('Reference'),
				'items': ['Request for Quotation', 'Supplier Quotation', 'Purchase Order']
			},
			{
				'label': _('Stock'),
				'items': ['Stock Entry', 'Purchase Receipt', 'Pick List']

			},
			{
				'label': _('Manufacturing'),
				'items': ['Work Order']
			}
		]
	}