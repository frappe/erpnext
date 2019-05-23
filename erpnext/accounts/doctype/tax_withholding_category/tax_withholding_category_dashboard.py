from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
		'fieldname': 'tax_withholding_category',
		'transactions': [
			{
				'label': _('Suppliers'),
				'items': ['Supplier']
			}
		]
	}
