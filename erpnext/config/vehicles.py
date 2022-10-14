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
					"name": "Customer",
					"onboard": 1,
					"description": _("Customer List."),
				},
				{
					"type": "doctype",
					"name": "Vehicle Booking Payment",
					"description": _("Payments for Vehicle Booking."),
					"dependencies": ["Vehicle Booking Order"],
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Vehicle Allocation Register",
					"doctype": "Vehicle Allocation",
					"dependencies": ["Vehicle Allocation"],
					"onboard": 1,
				},
			]
		},
		{
			"label": _("Pre Sales"),
			"items": [
				{
					"type": "doctype",
					"name": "Vehicle Quotation",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Lead",
					"description": _("Lead List."),
				},
				{
					"type": "doctype",
					"name": "Opportunity",
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
					"type": "report",
					"is_query_report": True,
					"name": "Vehicle Stock",
					"doctype": "Vehicle",
					"dependencies": ["Vehicle"],
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
			"label": _("Vehicle Service"),
			"items": [
				{
					"type": "doctype",
					"name": "Project",
					"onboard": 1,
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Vehicle Tracking Sheet",
					"doctype": "Vehicle",
					"dependencies": ["Vehicle"],
					"onboard": 1,
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Vehicle Service Summary",
					"doctype": "Project",
					"dependencies": ["Project"],
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Vehicle Service Receipt",
					"dependencies": ["Vehicle", "Project"],
				},
				{
					"type": "doctype",
					"name": "Vehicle Gate Pass",
					"dependencies": ["Vehicle", "Project"],
				},
			],
		},
		{
			"label": _("Vehicle Pre Service"),
			"items": [
				{
					"type": "doctype",
					"name": "Appointment",
					"onboard": 1,
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Appointment Sheet",
					"doctype": "Appointment",
					"dependencies": ["Appointment"],
					"onboard": 1,
				},
			],
		},
		{
			"label": _("Vehicle Registration"),
			"items": [
				{
					"type": "doctype",
					"name": "Vehicle Registration Order",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Vehicle Registration Receipt",
					"dependencies": ["Vehicle"],
				},
				{
					"type": "doctype",
					"name": "Vehicle Transfer Letter",
					"dependencies": ["Vehicle"],
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Vehicle Registration Register",
					"doctype": "Vehicle Registration Order",
					"dependencies": ["Vehicle Registration Order"],
				},
			],
		},
		{
			"label": _("Vehicle Documents"),
			"items": [
				{
					"type": "doctype",
					"name": "Vehicle Invoice",
				},
				{
					"type": "doctype",
					"name": "Vehicle Invoice Delivery",
				},
				{
					"type": "doctype",
					"name": "Vehicle Invoice Movement",
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
				{
					"type": "doctype",
					"name": "Project Workshop"
				},
			]
		},
		{
			"label": _("Reports"),
			"items": [
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
					"name": "Vehicle Booking Summary",
					"doctype": "Vehicle Booking Order",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Vehicle Booking Analytics",
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
				{
					"type": "report",
					"name": "Claim Items To Be Billed",
					"is_query_report": True,
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
					"name": "Vehicle Pricing Component",
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
		{
			"label": _("More / Work in Progress"),
			"icon": "fa fa-cog",
			"items": [
				{
					"type": "doctype",
					"name": "Vehicle Log",
					"dependencies": ["Vehicle"],
				},
			]
		},
	]