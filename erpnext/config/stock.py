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
					"name": "Material Request",
					"description": _("Requests for items."),
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
					"type": "page",
					"name": "stock-balance",
					"label": _("Stock Summary")
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Stock Ageing",
					"doctype": "Item",
				},

			]
		},
		{
			"label": _("Items and Pricing"),
			"items": [
				{
					"type": "doctype",
					"name": "Item",
					"description": _("All Products or Services."),
				},
				{
					"type": "doctype",
					"name": "Product Bundle",
					"description": _("Bundle items at time of sale."),
				},
				{
					"type": "doctype",
					"name": "Price List",
					"description": _("Price List master.")
				},
				{
					"type": "doctype",
					"name": "Item Group",
					"icon": "fa fa-sitemap",
					"label": _("Item Group"),
					"link": "Tree/Item Group",
					"description": _("Tree of Item Groups."),
				},
				{
					"type": "doctype",
					"name": "Item Price",
					"description": _("Multiple Item prices."),
					"route": "Report/Item Price"
				},
				{
					"type": "doctype",
					"name": "Shipping Rule",
					"description": _("Rules for adding shipping costs.")
				},
				{
					"type": "doctype",
					"name": "Pricing Rule",
					"description": _("Rules for applying pricing and discount.")
				},

			]
		},
		{
			"label": _("Serial No and Batch"),
			"items": [
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
				{
					"type": "doctype",
					"name": "Installation Note",
					"description": _("Installation record for a Serial No.")
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
				}
			]
		},
		{
			"label": _("Setup"),
			"icon": "fa fa-cog",
			"items": [
				{
					"type": "doctype",
					"name": "Stock Settings",
					"description": _("Default settings for stock transactions.")
				},
				{
					"type": "doctype",
					"name": "Warehouse",
					"description": _("Where items are stored."),
				},
				{
					"type": "doctype",
					"name": "UOM",
					"label": _("Unit of Measure") + " (UOM)",
					"description": _("e.g. Kg, Unit, Nos, m")
				},
				{
					"type": "doctype",
					"name": "Item Attribute",
					"description": _("Attributes for Item Variants. e.g Size, Color etc."),
				},
				{
					"type": "doctype",
					"name": "Brand",
					"description": _("Brand master.")
				},
			]
		},
		{
			"label": _("Analytics"),
			"icon": "fa fa-table",
			"items": [
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
					"icon": "fa fa-bar-chart"
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
			"label": _("Reports"),
			"icon": "fa fa-list",
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
					"name": "Batch Item Expiry Status",
					"doctype": "Stock Ledger Entry"
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
			]
		},
		{
			"label": _("Help"),
			"icon": "fa fa-facetime-video",
			"items": [
				{
					"type": "help",
					"label": _("Items and Pricing"),
					"youtube_id": "qXaEwld4_Ps"
				},
				{
					"type": "help",
					"label": _("Item Variants"),
					"youtube_id": "OGBETlCzU5o"
				},
				{
					"type": "help",
					"label": _("Opening Stock Balance"),
					"youtube_id": "0yPgrtfeCTs"
				},
				{
					"type": "help",
					"label": _("Making Stock Entries"),
					"youtube_id": "Njt107hlY3I"
				},
				{
					"type": "help",
					"label": _("Serialized Inventory"),
					"youtube_id": "gvOVlEwFDAk"
				},
				{
					"type": "help",
					"label": _("Batch Inventory"),
					"youtube_id": "J0QKl7ABPKM"
				},
				{
					"type": "help",
					"label": _("Managing Subcontracting"),
					"youtube_id": "ThiMCC2DtKo"
				},
			]
		}
	]
