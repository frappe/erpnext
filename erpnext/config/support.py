from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Issues"),
			"items": [
				{
					"type": "doctype",
					"name": "Issue",
					"description": _("Support queries from customers."),
				},
				{
					"type": "doctype",
					"name": "Communication",
					"description": _("Communication log."),
				},
			]
		},
		{
			"label": _("Warranty"),
			"items": [
				{
					"type": "doctype",
					"name": "Warranty Claim",
					"description": _("Warranty Claim against Serial No."),
				},
				{
					"type": "doctype",
					"name": "Serial No",
					"description": _("Single unit of an Item."),
				},
			]
		},
		{
			"label": _("Reports"),
			"icon": "fa fa-list",
			"items": [
				{
					"type": "page",
					"name": "support-analytics",
					"label": _("Support Analytics"),
					"icon": "fa fa-bar-chart"
				},
				{
					"type": "report",
					"name": "Minutes to First Response for Issues",
					"doctype": "Issue",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Support Hours",
					"doctype": "Issue",
					"is_query_report": True
				},
			]
		},
				{
			"label": _("Service Level Agreement"),
			"items": [
				{
					"type": "doctype",
					"name": "Employee Group",
					"description": _("Support Team."),
				},
				{
					"type": "doctype",
					"name": "Service Level",
					"description": _("Service Level."),
				},
				{
					"type": "doctype",
					"name": "Support Contract",
					"description": _("Support Contract."),
				},
				{
					"type": "doctype",
					"name": "Service Level Agreement",
					"description": _("Service Level Agreement."),
				}
			]
		},
	]
