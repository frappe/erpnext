from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("PersonaDetails"),
			"items": [
				{
					"type": "doctype",
					"name": "Qualification",
					"description": _("Personal Details."),
					"onboard": 1,
				},
				
				
				
			]
		},
		
	
		{
			"label": _("Reports"),
			"icon": "fa fa-list",
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Open Work Orders",
					"doctype": "Work Order"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Work Orders in Progress",
					"doctype": "Work Order"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Issued Items Against Work Order",
					"doctype": "Work Order"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Completed Work Orders",
					"doctype": "Work Order"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Production Analytics",
					"doctype": "Work Order"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "BOM Search",
					"doctype": "BOM"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "BOM Stock Report",
					"doctype": "BOM"
				}
			]
		},
		
	]
