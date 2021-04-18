from __future__ import unicode_literals
import frappe

def get_data():
	vehicle_domain_sections = []
	if 'Vehicles' in frappe.get_active_domains():
		vehicle_domain_sections = [
			{
				'label': ['Reference'],
				'items': ['Vehicle Booking Order', 'Project']
			},
			{
				'label': ['Vehicle Transaction'],
				'items': ['Vehicle Receipt', 'Vehicle Delivery']
			},
			{
				'label': ['Transfer'],
				'items': ['Vehicle Transfer Letter']
			},
			{
				'label': ['Accounting Entries'],
				'items': ['Journal Entry', 'Payment Entry']
			},
		]

	return {
		'fieldname': 'vehicle',
		'non_standard_fieldnames': {
			'Project': 'applies_to_vehicle',
			'Journal Entry': 'applies_to_vehicle',
			'Payment Entry': 'applies_to_vehicle',
		},
		'transactions': vehicle_domain_sections + [
			{
				'label': ['Sales'],
				'items': ['Delivery Note', 'Sales Invoice']
			},
			{
				'label': ['Purchase'],
				'items': ['Purchase Receipt', 'Purchase Invoice']
			},
			{
				'label': ['Movement'],
				'items': ['Stock Entry', 'Vehicle Log']
			},
		]
	}
