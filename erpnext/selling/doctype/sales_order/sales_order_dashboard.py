from frappe import _

def get_data():
	return {
		'fieldname': 'sales_order',
		'non_standard_fieldnames': {
			'Delivery Note': 'against_sales_order',
			'Journal Entry': 'reference_name',
			'Payment Entry': 'reference_name',
			'Payment Request': 'reference_name'
		},
		'internal_links': {
			'Quotation': ['items', 'prevdoc_docname']
		},
		'transactions': [
			{
				'label': _('Fulfillment'),
				'items': ['Sales Invoice', 'Delivery Note']
			},
			{
				'label': _('Purchasing'),
				'items': ['Material Request', 'Purchase Order']
			},
			{
				'label': _('Projects'),
				'items': ['Project']
			},
			{
				'label': _('Manufacturing'),
				'items': ['Production Order']
			},
			{
				'label': _('Reference'),
				'items': ['Quotation']
			},
			{
				'label': _('Payment'),
				'items': ['Payment Entry', 'Payment Request', 'Journal Entry']
			},
		]
	}