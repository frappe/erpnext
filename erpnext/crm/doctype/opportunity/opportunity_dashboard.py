from __future__ import unicode_literals
import frappe
from frappe import _

def get_data():
	vehicle_domain_links = []
	if 'Vehicles' in frappe.get_active_domains():
		vehicle_domain_links.append({
			'label': _('Vehicle Booking'),
			'items': ['Vehicle Quotation', 'Vehicle Booking Order']
		})

	return {
		'fieldname': 'opportunity',
		'internal_links': {
			'Maintenance Schedule': 'maintenance_schedule'
		},
		'transactions': [
			{
				'label': _("Pre Sales"),
				'items': ['Quotation', 'Supplier Quotation']
			},
		] + vehicle_domain_links + [
			{
				'label': _("Reference"),
				'items': ['Appointment', 'Maintenance Schedule']
			},
		]
	}
