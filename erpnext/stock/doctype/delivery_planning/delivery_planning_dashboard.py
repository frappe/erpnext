from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'sales_order',
		'non_standard_fieldnames': {
			'Delivery Note': 'against_sales_order',
			#'Journal Entry': 'reference_name',
			# 'Payment Entry': 'reference_name',
			# 'Payment Request': 'reference_name',
			# 'Auto Repeat': 'reference_document',
			# 'Maintenance Visit': 'prevdoc_docname'
		},
		# 'internal_links': {
		# 	'Quotation': ['items', 'prevdoc_docname']
		# },
		'transactions': [
			{
				'label': _('Fulfillment'),
				'items': ['Pick List', 'Delivery Note']
			},
			{
				'label': _('Purchasing'),
				'items': ['Purchase Order']
			}
		]
	}
