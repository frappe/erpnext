from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Documents"),
			"icon": "icon-star",
			"items": [
				{
					"type": "doctype",
					"name": "Material Request",
					"description": _("Requests for items."),
				},
				{
					"type": "doctype",
					"name": "Stock Entry",
					"description": _("Record item movement."),
				},
				{
					"type": "doctype",
					"name": "Delivery Note",
					"description": _("Shipments to customers."),
				},
				{
					"type": "doctype",
					"name": "Purchase Receipt",
					"description": _("Goods received from Suppliers."),
				},
				{
					"type": "doctype",
					"name": "Installation Note",
					"description": _("Installation record for a Serial No.")
				},
				{
					"type": "doctype",
					"name": "Item",
					"description": _("All Products or Services."),
				},
				{
					"type": "doctype",
					"name": "Warehouse",
					"description": _("Where items are stored."),
				},
				{
					"type": "doctype",
					"name": "Serial No",
					"description": _("Single unit of an Item."),
				},
				{
					"type": "doctype",
					"name": "Batch",
					"description": _("Batch (lot) of an Item."),
				},
			]
		},
		{
			"label": _("Tools"),
			"icon": "icon-wrench",
			"items": [
				{
					"type": "doctype",
					"name": "Stock Reconciliation",
					"description": _("Upload stock balance via csv.")
				},
				{
					"type": "doctype",
					"name": "Packing Slip",
					"description": _("Split Delivery Note into packages.")
				},
				{
					"type": "doctype",
					"name": "Quality Inspection",
					"description": _("Incoming quality inspection.")
				},
				{
					"type": "doctype",
					"name": "Landed Cost Voucher",
					"description": _("Update additional costs to calculate landed cost of items"),
				},
				{
					"type": "doctype",
					"name": "Stock UOM Replace Utility",
					"description": _("Change UOM for an Item."),
				}
			]
		},
		{
			"label": _("Setup"),
			"icon": "icon-cog",
			"items": [
				{
					"type": "doctype",
					"name": "Stock Settings",
					"description": _("Default settings for stock transactions.")
				},
				{
					"type": "page",
					"name": "Sales Browser",
					"icon": "icon-sitemap",
					"label": _("Item Group Tree"),
					"link": "Sales Browser/Item Group",
					"description": _("Tree of Item Groups."),
					"doctype": "Item Group",
				},
				{
					"type": "doctype",
					"name": "UOM",
					"label": _("Unit of Measure") + " (UOM)",
					"description": _("e.g. Kg, Unit, Nos, m")
				},
				{
					"type": "doctype",
					"name": "Warehouse",
					"description": _("Warehouses.")
				},
				{
					"type": "doctype",
					"name": "Brand",
					"description": _("Brand master.")
				},
				{
					"type": "doctype",
					"name": "Price List",
					"description": _("Price List master.")
				},
				{
					"type": "doctype",
					"name": "Item Price",
					"description": _("Multiple Item prices."),
					"route": "Report/Item Price"
				},
				{
					"type": "doctype",
					"name": "Item Attribute",
					"description": _("Attributes for Item Variants. e.g Size, Color etc."),
				},
			]
		},
		{
			"label": _("Main Reports"),
			"icon": "icon-table",
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Stock Ledger",
					"doctype": "Stock Ledger Entry",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Stock Balance",
					"doctype": "Stock Ledger Entry"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Stock Projected Qty",
					"doctype": "Item",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Stock Ageing",
					"doctype": "Item",
				},
				{
					"type": "report",
					"is_query_report": False,
					"name": "Item-wise Price List Rate",
					"doctype": "Item Price",
				},
				{
					"type": "page",
					"name": "stock-analytics",
					"label": _("Stock Analytics"),
					"icon": "icon-bar-chart"
				}
			]
		},
		{
			"label": _("Standard Reports"),
			"icon": "icon-list",
			"items": [
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
					"name": "Item Shortage Report",
					"route": "Report/Bin/Item Shortage Report",
					"doctype": "Purchase Receipt"
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
				{
					"type": "report",
					"is_query_report": True,
					"name": "Requested Items To Be Transferred",
					"doctype": "Material Request"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Batch-Wise Balance History",
					"doctype": "Batch"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Item Prices",
					"doctype": "Price List"
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
					"name": "Delivery Note Trends",
					"doctype": "Delivery Note"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Purchase Receipt Trends",
					"doctype": "Purchase Receipt"
				},
			]
		},
		{
			"label": _("Help"),
			"icon": "icon-facetime-video",
			"items": [
				{
					"type": "help",
					"label": _("Items and Pricing"),
					"youtube_id": "qXaEwld4_Ps"
				},
				{
					"type": "help",
					"label": _("Opening Stock Balance"),
					"youtube_id": "0yPgrtfeCTs"
				},
				{
					"type": "help",
					"label": _("Item Variants"),
					"youtube_id": "OGBETlCzU5o"
				},
			]
		}
	]
