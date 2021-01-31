from __future__ import unicode_literals
import frappe

def get_data():
	project_link = []
	if 'Vehicles' in frappe.get_active_domains():
		project_link.append('Project')

	return {
		'fieldname': 'vehicle',
		'non_standard_fieldnames': {
			'Project': 'applies_to_vehicle',
		},
		'transactions': [
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
			{
				'label': ['Reference'],
				'items': ['Vehicle Booking Order'] + project_link
			},
		]
	}
