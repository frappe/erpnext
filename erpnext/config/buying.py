from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Items and Pricing"),
			"items": [
				{
					"type": "doctype",
					"name": "Item",
					"onboard": 1,
					"description": _("All Products or Services."),
				},
				{
					"type": "doctype",
					"name": "Item Price",
					"description": _("Multiple Item prices."),
					"onboard": 1,
					"route": "Report/Item Price"
				},
				{
					"type": "doctype",
					"name": "Price List",
					"description": _("Price List master.")
				},
				{
					"type": "doctype",
					"name": "Product Bundle",
					"description": _("Bundle items at time of sale."),
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
					"name": "Pricing Rule",
					"description": _("Rules for applying pricing and discount.")
				},
			]
		},
		{
			"label": _("Purchasing"),
			"icon": "fa fa-star",
			"items": [
				{
					"type": "doctype",
					"name": "Purchase Order",
					"onboard": 1,
					"dependencies": ["Item", "Supplier"],
					"description": _("Purchase Orders given to Suppliers."),
				},
				{
					"type": "doctype",
					"name": "Material Request",
					"onboard": 1,
					"dependencies": ["Item"],
					"description": _("Request for purchase."),
				},
				{
					"type": "doctype",
					"name": "Request for Quotation",
					"onboard": 1,
					"dependencies": ["Item", "Supplier"],
					"description": _("Request for quotation."),
				},
				{
					"type": "doctype",
					"name": "Supplier Quotation",
					"dependencies": ["Item", "Supplier"],
					"description": _("Quotations received from Suppliers."),
				},
			]
		},
		{
			"label": _("Supplier"),
			"items": [
				{
					"type": "doctype",
					"name": "Supplier",
					"onboard": 1,
					"description": _("Supplier database."),
				},
				{
					"type": "doctype",
					"name": "Supplier Group",
					"description": _("Supplier Group master.")
				},
				{
					"type": "doctype",
					"name": "Contact",
					"description": _("All Contacts."),
				},
				{
					"type": "doctype",
					"name": "Address",
					"description": _("All Addresses."),
				},

			]
		},
		{
			"label": _("Setup"),
			"icon": "fa fa-cog",
			"items": [
				{
					"type": "doctype",
					"name": "Buying Settings",
					"onboard": 1,
					"description": _("Default settings for buying transactions.")
				},
				{
					"type": "doctype",
					"name":"Terms and Conditions",
					"label": _("Terms and Conditions Template"),
					"description": _("Template of terms or contract.")
				},
				{
					"type": "doctype",
					"name": "Purchase Taxes and Charges Template",
					"description": _("Tax template for buying transactions.")
				},
			]
		},
		{
			"label": _("Analytics"),
			"icon": "fa fa-table",
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Purchase Analytics",
					"reference_doctype": "Purchase Order",
					"onboard": 1
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Supplier-Wise Sales Analytics",
					"reference_doctype": "Stock Ledger Entry",
					"onboard": 1
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Purchase Order Trends",
					"reference_doctype": "Purchase Order",
					"onboard": 1,
				},
			]
		},
		{
			"label": _("Supplier Scorecard"),
			"items": [
				{
					"type": "doctype",
					"name": "Supplier Scorecard",
					"description": _("All Supplier scorecards."),
				},
				{
					"type": "doctype",
					"name": "Supplier Scorecard Variable",
					"description": _("Templates of supplier scorecard variables.")
				},
				{
					"type": "doctype",
					"name": "Supplier Scorecard Criteria",
					"description": _("Templates of supplier scorecard criteria."),
				},
				{
					"type": "doctype",
					"name": "Supplier Scorecard Standing",
					"description": _("Templates of supplier standings."),
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
					"name": "Items To Be Requested",
					"reference_doctype": "Item",
					"onboard": 1,
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Requested Items To Be Ordered",
					"reference_doctype": "Material Request",
					"onboard": 1,
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Item-wise Purchase History",
					"reference_doctype": "Item",
					"onboard": 1,
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Material Requests for which Supplier Quotations are not created",
					"reference_doctype": "Material Request"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Address And Contacts",
					"label": "Supplier Addresses And Contacts",
					"reference_doctype": "Address",
					"route_options": {
						"party_type": "Supplier"
					}
				}
			]
		},
		{
			"label": _("Help"),
			"items": [
				{
					"type": "help",
					"label": _("Customer and Supplier"),
					"youtube_id": "anoGi_RpQ20"
				},
				{
					"type": "help",
					"label": _("Material Request to Purchase Order"),
					"youtube_id": "4TN9kPyfIqM"
				},
				{
					"type": "help",
					"label": _("Purchase Order to Payment"),
					"youtube_id": "EK65tLdVUDk"
				},
				{
					"type": "help",
					"label": _("Managing Subcontracting"),
					"youtube_id": "ThiMCC2DtKo"
				},
			]
		},
	]
