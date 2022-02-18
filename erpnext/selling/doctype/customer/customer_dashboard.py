
from frappe import _


def get_data():
	return {
		'heatmap': False,
		'heatmap_message': _('This is based on transactions against this Customer. See timeline below for details'),
		'fieldname': 'customer',
		'non_standard_fieldnames': {
			'Payment Entry': 'party',
			'Quotation': 'party_name',
			'Opportunity': 'party_name',
			'Medical Objects': 'customer_id',
			'Sample': 'practitioner_id',
			'Bank Account': 'party',
			'Subscription': 'party'
		},
		'dynamic_links': {
			'party_name': ['Customer', 'quotation_to']
		},
		'transactions': [
			# {
			# 	'label': _('Pre Sales'),
			# 	'items': ['Opportunity', 'Quotation']
			# },
			{
				'label': _('Pricing/Payments'),
				'items': ['Pricing Rule', 'Payment Entry']
			},
			{
				'label': _('Orders'),
				'items': ['Sales Invoice', 'Backorder']
			},
			# {
			# 	'label': _('Support'),
			# 	'items': ['Issue']
			# },
			# {
			# 	'label': _('Projects'),
			# 	'items': ['Project']
			# },
			{
				'label': _('CRM'),
				'items': ["Interactions", "Memos", "Annual Plan"]
			},
			{
				'label': _('Statements'),
				'items': ['Customer Statements'],
				'label': _('Payments'),
				'items': ['Payment Entry', 'Bank Account']
			},
			{
				'label': _('Support'),
				'items': ['Issue', 'Maintenance Visit', 'Installation Note', 'Warranty Claim']
			},
			{
				'label': 'Testing DB',
				'items': ['Medical Objects', 'Sample']
			}
			# {
			# 	'label': _('Subscriptions'),
			# 	'items': ['Subscription']
			# }
		]
	}
