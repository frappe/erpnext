from __future__ import unicode_literals
import frappe
from frappe import _

def get_data():
	config =  [
		{
			"label": _("Purchasing Transactions"),
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
					"name": "Purchase Receipt",
					"dependencies": ["Item", "Supplier"]
				},
				{
					"type": "doctype",
					"name": "Purchase Invoice",
					"dependencies": ["Item", "Supplier"]
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
			"label": _("Suppliers"),
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
				{
					"type": "report",
					"is_query_report": True,
					"name": "Address And Contacts",
					"label": _("Supplier Addresses And Contacts"),
					"reference_doctype": "Address",
					"route_options": {
						"party_type": "Supplier"
					}
				}
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
					"name": "Brand",
				},
				{
					"type": "doctype",
					"name": "Product Bundle",
					"description": _("Bundle items at time of sale."),
					"dependencies": ["Item"],
				},
			]
		},
		{
			"label": _("Pricing"),
			"items": [
				{
					"type": "doctype",
					"name": "Price List",
					"description": _("Price List master."),
					"onboard": 1,
				},
				{
					"type": "report",
					"label": _("Price List Editor"),
					"name": "Item Prices",
					"is_query_report": True,
					"dependencies": ["Item", "Price List"],
					"onboard": 1,
					"route_options": {
						"buying_selling": "Buying"
					}
				},
				{
					"type": "doctype",
					"name": "Item Price",
					"label": _("All Item Prices"),
					"description": _("Multiple Item prices."),
					"route": "#Report/Item Price",
					"dependencies": ["Item", "Price List"],
				},
				{
					"type": "doctype",
					"name": "Promotional Scheme",
					"description": _("Rules for applying different promotional schemes.")
				},
				{
					"type": "doctype",
					"name": "Pricing Rule",
					"description": _("Rules for applying pricing and discount."),
					"dependencies": ["Item"],
				},
				{
					"type": "doctype",
					"name": "Shipping Rule",
					"description": _("Rules for adding shipping costs."),
				},
			]
		},
		{
			"label": _("Settings"),
			"icon": "fa fa-cog",
			"items": [
				{
					"type": "doctype",
					"name": "Buying Settings",
					"settings": 1,
					"description": _("Default settings for buying transactions.")
				},
				{
					"type": "doctype",
					"name": "Purchase Taxes and Charges Template",
					"description": _("Tax template for buying transactions.")
				},
				{
					"type": "doctype",
					"name":"Terms and Conditions",
					"label": _("Terms and Conditions Template"),
					"description": _("Template of terms or contract.")
				},
			]
		},
		{
			"label": _("Key Reports"),
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
					"name": "Purchase Details",
					"reference_doctype": "Purchase Order",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Procurement Tracker",
					"reference_doctype": "Purchase Order",
					"onboard": 1,
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Requested Items To Be Ordered",
					"reference_doctype": "Material Request",
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
					"name": "Item-wise Purchase History",
					"reference_doctype": "Item",
					"onboard": 1,
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
					"name": "Material Requests for which Supplier Quotations are not created",
					"reference_doctype": "Material Request"
				}
			]
		},

	]

	regional = {
			"label": _("Regional"),
			"items": [
				{
				"type": "doctype",
				"name": "Import Supplier Invoice",
				"description": _("Import Italian Supplier Invoice."),
				"onboard": 1,
				}
			]
		}

	countries = frappe.get_all("Company", fields="country")
	countries = [country["country"] for country in countries]
	if "Italy" in countries:
		config.append(regional)
	return config