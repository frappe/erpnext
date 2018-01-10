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
				},
				{
					"type": "doctype",
					"name": "Delivery Note",
				},
				{
					"type": "doctype",
					"name": "Purchase Receipt",
				},
				{
					"type": "doctype",
					"name": "Material Request",
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
				{
					"type": "report",
					"is_query_report": True,
					"name": "Item Price Stock",
					"doctype": "Item",
				}
			]
		},
		{
			"label": _("Items and Pricing"),
			"items": [
				{
					"type": "doctype",
					"name": "Item",
				},
				{
					"type": "doctype",
					"name": "Product Bundle",
				},
				{
					"type": "doctype",
					"name": "Price List",
				},
				{
					"type": "doctype",
					"name": "Item Group",
					"icon": "fa fa-sitemap",
					"label": _("Item Group"),
					"link": "Tree/Item Group",
				},
				{
					"type": "doctype",
					"name": "Item Price",
					"route": "Report/Item Price"
				},
				{
					"type": "doctype",
					"name": "Shipping Rule",
				},
				{
					"type": "doctype",
					"name": "Pricing Rule",
				},
				{
					"type": "doctype",
					"name": "Item Variant Settings",
				},
			]
		},
		{
			"label": _("Serial No and Batch"),
			"items": [
				{
					"type": "doctype",
					"name": "Serial No",
				},
				{
					"type": "doctype",
					"name": "Batch",
				},
				{
					"type": "doctype",
					"name": "Installation Note",
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
			"label": _("Fulfilment"),
			"items": [
				{
					"type": "doctype",
					"name": "Delivery Trip",
					"description": _("Delivery Trip service tours to customers.")
				}
			]
		},
		{
			"label": _("Tools"),
			"icon": "fa fa-wrench",
			"items": [
				{
					"type": "doctype",
					"name": "Stock Reconciliation",
				},
				{
					"type": "doctype",
					"name": "Packing Slip",
				},
				{
					"type": "doctype",
					"name": "Quality Inspection",
				},
				{
					"type": "doctype",
					"name": "Landed Cost Voucher",
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
				},
				{
					"type": "doctype",
					"name": "Warehouse",
				},
				{
					"type": "doctype",
					"name": "UOM",
					"label": _("Unit of Measure") + " (UOM)",
				},
				{
					"type": "doctype",
					"name": "Item Attribute",
				},
				{
					"type": "doctype",
					"name": "Brand",
				},
				{
					"type": "doctype",
					"name": "Item Variant Settings",
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
				{
					"type": "report",
					"is_query_report": True,
					"name": "Item Variant Details",
					"doctype": "Item"
				}
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
