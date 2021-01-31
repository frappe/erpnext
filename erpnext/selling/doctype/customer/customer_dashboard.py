from __future__ import unicode_literals

import frappe
from frappe import _


def get_data():
	vehicle_domain_links = []
	vbo_link = []
	if 'Vehicles' in frappe.get_active_domains():
		vbo_link.append("Vehicle Booking Order")
		vehicle_domain_links.append({
			'label': _('Vehicles'),
			'items': ['Vehicle']
		})

	return {
		'heatmap': True,
		'heatmap_message': _('This is based on transactions against this Customer. See timeline below for details'),
		'fieldname': 'customer',
		'non_standard_fieldnames': {
			'Payment Entry': 'party',
			'Journal Entry': 'party',
			'Sales Invoice': 'bill_to',
			'Quotation': 'party_name',
			'Opportunity': 'party_name'
		},
		'dynamic_links': {
			'party_name': ['Customer', 'quotation_to']
		},
		'transactions': [
			{
				'label': _('Pre Sales'),
				'items': vbo_link + ['Opportunity', 'Quotation']
			},
			{
				'label': _('Orders'),
				'items': ['Sales Order', 'Delivery Note', 'Sales Invoice']
			},
			{
				'label': _('Payments and Vouchers'),
				'items': ['Payment Entry', 'Journal Entry']
			},
			{
				'label': _('Support'),
				'items': ['Issue']
			},
			{
				'label': _('Projects'),
				'items': ['Project']
			},
			{
				'label': _('Pricing'),
				'items': ['Pricing Rule']
			},
			{
				'label': _('Subscriptions'),
				'items': ['Subscription']
			}
		] + vehicle_domain_links
	}
