
from frappe import _


def get_data():
	return {
		'fieldname': 'tax_category',
		'transactions': [
			{
				'label': _('Applied On'),
				'items': ['Item Default Rule', 'Tax Rule', 'Customs Tariff Number']
			},
			{
				'label': _('Pre Sales'),
				'items': ['Quotation', 'Supplier Quotation']
			},
			{
				'label': _('Sales'),
				'items': ['Sales Invoice', 'Delivery Note', 'Sales Order']
			},
			{
				'label': _('Purchase'),
				'items': ['Purchase Invoice', 'Purchase Receipt', 'Purchase Order']
			},
			{
				'label': _('Party'),
				'items': ['Customer', 'Supplier']
			},
		]
	}
