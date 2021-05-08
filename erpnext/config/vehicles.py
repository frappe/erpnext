from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Booking"),
			"items": [
				{
					"type": "doctype",
					"name": "Vehicle Booking Order",
					"onboard": 1
				},
				{
					"type": "doctype",
					"name": "Vehicle Booking Payment",
					"description": _("Payments for Vehicle Booking."),
					"dependencies": ["Vehicle Booking Order"],
				},
				{
					"type": "doctype",
					"name": "Customer",
					"onboard": 1,
					"description": _("Customer List."),
				},
			]
		},
		{
			"label": _("Stock"),
			"items": [
				{
					"type": "doctype",
					"name": "Vehicle",
					"description": _("Vehicle List."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Vehicle Receipt",
					"dependencies": ["Vehicle"],
				},
				{
					"type": "doctype",
					"name": "Vehicle Delivery",
					"dependencies": ["Vehicle"],
				},
			],
		},
		{
			"label": _("Vehicle Documents"),
			"items": [
				{
					"type": "doctype",
					"name": "Vehicle Invoice Receipt",
					"dependencies": ["Vehicle Booking Order"],
				},
				{
					"type": "doctype",
					"name": "Vehicle Invoice Delivery",
					"dependencies": ["Vehicle Booking Order"],
				},
				{
					"type": "doctype",
					"name": "Vehicle Transfer Letter",
					"dependencies": ["Vehicle"],
				},
			],
		},
		{
			"label": _("Masters"),
			"items": [
				{
					"type": "doctype",
					"name": "Item",
					"label": _("Vehicle Item (Variants and Models)"),
					"description": _("Vehicle Item (Models and Variant) List"),
					"onboard": 1,
					"route_options": {
						"is_vehicle": 1
					}
				},
				{
					"type": "doctype",
					"name": "Vehicle Allocation Period",
				},
				{
					"type": "doctype",
					"name": "Vehicle Allocation"
				},
			]
		},
		{
			"label": _("Key Reports"),
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Vehicle Allocation Register",
					"doctype": "Vehicle Allocation",
					"dependencies": ["Vehicle Allocation"],
					"onboard": 1,
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Vehicle Stock",
					"doctype": "Vehicle",
					"dependencies": ["Vehicle"],
					"onboard": 1,
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Vehicle Booking Details",
					"doctype": "Vehicle Booking Order",
					"dependencies": ["Vehicle Booking Order"],
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Vehicle Booking Deposit Summary",
					"doctype": "Vehicle Booking Payment",
					"dependencies": ["Vehicle Booking Payment"],
				},
			]
		},
		{
			"label": _("Summary Reports"),
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Vehicle Booking Analytics",
					"doctype": "Vehicle Booking Order",
					"dependencies": ["Vehicle Booking Order"],
				},
			]
		},
		{
			"label": _("Settings"),
			"icon": "fa fa-cog",
			"items": [
				{
					"type": "doctype",
					"name": "Vehicles Settings",
				},
				{
					"type": "doctype",
					"name": "Vehicle Withholding Tax Rule",
				},
				{
					"type": "doctype",
					"name": "Vehicle Allocation Creation Tool",
				},
			]
		},
	]