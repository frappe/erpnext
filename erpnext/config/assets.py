from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Assets"),
			"items": [
				{
					"type": "doctype",
					"name": "Asset",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Location",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Asset Category",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Asset Settings",
				},
				{
					"type": "doctype",
					"name": "Asset Movement",
					"description": _("Transfer an asset from one warehouse to another")
				},
			]
		},
		{
			"label": _("Maintenance"),
			"items": [
				{
					"type": "doctype",
					"name": "Asset Maintenance Team",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Asset Maintenance",
					"onboard": 1,
					"dependencies": ["Asset Maintenance Team"],
				},
				{
					"type": "doctype",
					"name": "Asset Maintenance Tasks",
					"onboard": 1,
					"dependencies": ["Asset Maintenance"],
				},
				{
					"type": "doctype",
					"name": "Asset Maintenance Log",
					"dependencies": ["Asset Maintenance"],
				},
				{
					"type": "doctype",
					"name": "Asset Value Adjustment",
					"dependencies": ["Asset"],
				},
				{
					"type": "doctype",
					"name": "Asset Repair",
					"dependencies": ["Asset"],
				},
			]
		},
		{
			"label": _("Reports"),
			"icon": "fa fa-table",
			"items": [
				{
					"type": "report",
					"name": "Asset Depreciation Ledger",
					"doctype": "Asset",
					"is_query_report": True,
					"dependencies": ["Asset"],
				},
				{
					"type": "report",
					"name": "Asset Depreciations and Balances",
					"doctype": "Asset",
					"is_query_report": True,
					"dependencies": ["Asset"],
				},
				{
					"type": "report",
					"name": "Asset Maintenance",
					"doctype": "Asset Maintenance",
					"dependencies": ["Asset Maintenance"]
				},
			]
		}
	]
