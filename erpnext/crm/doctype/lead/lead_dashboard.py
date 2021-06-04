from __future__ import unicode_literals
import frappe
from frappe import _

def get_data():
	vehicle_domain_links = []
	if 'Vehicles' in frappe.get_active_domains():
		vehicle_domain_links.append({
			'label': _('Pre Booking'),
			'items': ['Vehicle Quotation']
		})

	return {
		'fieldname': 'lead',
		'non_standard_fieldnames': {
			'Quotation': 'party_name',
			'Opportunity': 'party_name',
			'Vehicle Quotation': 'party_name',
		},
		'dynamic_links': {
			'party_name': ['Lead', 'quotation_to']
		},
		'transactions': [
			{
				'label': _('Pre Sales'),
				'items': ['Opportunity', 'Quotation']
			},
		] + vehicle_domain_links
	}
