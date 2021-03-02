from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Stock Transactions"),
			"items": [
				{
					"type": "doctype",
					"name": "Stock Entry",
					"onboard": 1,
					"dependencies": ["Item"],
				},
				{
					"type": "doctype",
					"name": "Delivery Note",
					"onboard": 1,
					"dependencies": ["Item", "Customer"],
				},
				{
					"type": "doctype",
					"name": "Purchase Receipt",
					"onboard": 1,
					"dependencies": ["Item", "Supplier"],
				},
				{
					"type": "doctype",
					"name": "Material Request",
					"onboard": 1,
					"dependencies": ["Item"],
				},
				{
					"type": "doctype",
					"name": "Pick List",
					"onboard": 1,
					"dependencies": ["Item"],
				},
				{
					"type": "doctype",
					"name": "Delivery Trip"
				},
			]
		},
		{
			"label": _("Items"),
			"items": [
				{
					"type": "doctype",
					"name": "Item",
					"description": _("All Products or Services."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Item Group",
					"icon": "fa fa-sitemap",
					"label": _("Item Group"),
					"link": "Tree/Item Group",
					"description": _("Tree of Item Groups."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Product Bundle",
					"description": _("Bundle items at time of sale."),
					"dependencies": ["Item"],
				},
				{
					"type": "doctype",
					"name": "Item Alternative",
				},
				{
					"type": "doctype",
					"name": "Item Manufacturer",
				},
				{
					"type": "doctype",
					"name": "Item Attribute",
				},
			]
		},
		{
			"label": _("Stock Reports"),
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Stock Ledger",
					"doctype": "Stock Ledger Entry",
					"onboard": 1,
					"dependencies": ["Item"],
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Stock Balance",
					"doctype": "Stock Ledger Entry",
					"onboard": 1,
					"dependencies": ["Item"],
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Stock Projected Qty",
					"doctype": "Item",
					"onboard": 1,
					"dependencies": ["Item"],
				},
				{
					"type": "page",
					"name": "stock-balance",
					"label": _("Stock Summary"),
					"dependencies": ["Item"],
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Stock Ageing",
					"doctype": "Item",
					"dependencies": ["Item"],
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Batch Balance",
					"doctype": "Batch",
					"dependencies": ["Item", "Batch"],
				}
			]
		},
		{
			"label": _("Settings"),
			"icon": "fa fa-cog",
			"items": [
				{
					"type": "doctype",
					"name": "Stock Settings",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Warehouse",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Warehouse Type",
				},
				{
					"type": "doctype",
					"name": "UOM",
					"label": _("Unit of Measure") + " (UOM)",
				},
				{
					"type": "doctype",
					"name": "Item Variant Settings",
				},
				{
					"type": "doctype",
					"name": "Stock Entry Type",
				},
				{
					"type": "doctype",
					"name": "Transaction Type",
				},
			]
		},
		{
			"label": _("Pricing"),
			"items": [
				{
					"type": "doctype",
					"name": "Price List",
				},
				{
					"type": "report",
					"label": _("Price List Editor"),
					"name": "Item Prices",
					"is_query_report": True,
					"dependencies": ["Item", "Price List"]
				},
				{
					"type": "doctype",
					"name": "Item Price",
				},
				{
					"type": "doctype",
					"name": "Shipping Rule",
				},
				{
					"type": "doctype",
					"name": "Pricing Rule",
				},
			]
		},
		{
			"label": _("Serial No and Batch"),
			"items": [
				{
					"type": "doctype",
					"name": "Serial No",
					"onboard": 1,
					"dependencies": ["Item"],
				},
				{
					"type": "doctype",
					"name": "Batch",
					"onboard": 1,
					"dependencies": ["Item"],
				},
				{
					"type": "doctype",
					"name": "Installation Note",
					"dependencies": ["Item"],
				},
				{
					"type": "report",
					"name": "Serial No Service Contract Expiry",
					"doctype": "Serial No"
				},
				{
					"type": "report",
					"name": "Serial No Status",
					"doctype": "Serial No"
				},
				{
					"type": "report",
					"name": "Serial No Warranty Expiry",
					"doctype": "Serial No"
				},
			]
		},
		{
			"label": _("Tools"),
			"icon": "fa fa-wrench",
			"items": [
				{
					"type": "doctype",
					"name": "Stock Reconciliation",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Landed Cost Voucher",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Packing Slip",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Quality Inspection",
				},
				{
					"type": "doctype",
					"name": "Quality Inspection Template",
				},
				{
					"type": "doctype",
					"name": "Quick Stock Balance",
				},
			]
		},
		{
			"label": _("Key Reports"),
			"icon": "fa fa-table",
			"items": [
				{
					"type": "report",
					"is_query_report": False,
					"name": "Item-wise Price List Rate",
					"doctype": "Item Price",
					"onboard": 1,
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Stock Analytics",
					"onboard": 1,
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Ordered Items To Be Delivered",
					"doctype": "Delivery Note"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Purchase Order Items To Be Received",
					"doctype": "Purchase Receipt"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Item Shortage Report",
					"doctype": "Bin"
				},
			]
		},
		{
			"label": _("Other Reports"),
			"icon": "fa fa-list",
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Requested Items To Be Transferred",
					"doctype": "Material Request"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Batch Item Expiry Status",
					"doctype": "Stock Ledger Entry"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Itemwise Recommended Reorder Level",
					"doctype": "Item"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Item Variant Details",
					"doctype": "Item"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Subcontracted Raw Materials To Be Transferred",
					"doctype": "Purchase Order"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Subcontracted Item To Be Received",
					"doctype": "Purchase Order"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Stock and Account Value Comparison",
					"doctype": "Stock Ledger Entry"
				}
			]
		},

	]
