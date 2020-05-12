from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
		'heatmap': False,
		'heatmap_message': _('This is based on transactions against this Customer. See timeline below for details'),
		'fieldname': 'customer',
		'non_standard_fieldnames': {
			'Payment Entry': 'party',
			'Quotation': 'party_name',
			'Opportunity': 'party_name'
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
				'items': ["Interactions"]
			},
			# {
			# 	'label': _('Subscriptions'),
			# 	'items': ['Subscription']
			# }
		]
	}
