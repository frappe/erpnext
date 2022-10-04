from __future__ import unicode_literals
import frappe
from frappe import _

def get_data():
	out = [
		{
			"label": _("Sales Transactions"),
			"icon": "fa fa-star",
			"items": [
				{
					"type": "doctype",
					"name": "Sales Order",
					"description": _("Confirmed orders from Customers."),
					"onboard": 1,
					"dependencies": ["Item", "Customer"],
				},
				{
					"type": "doctype",
					"name": "Delivery Note",
					"dependencies": ["Item", "Customer"],
				},
				{
					"type": "doctype",
					"name": "Sales Invoice",
					"description": _("Invoices for Costumers."),
					"dependencies": ["Item", "Customer"],
				},
				{
					"type": "doctype",
					"name": "Quotation",
					"description": _("Quotes to Leads or Customers."),
					"onboard": 1,
					"dependencies": ["Item", "Customer"],
				},
			]
		},
		{
			"label": _("Customers"),
			"items": [
				{
					"type": "doctype",
					"name": "Customer",
					"description": _("Customer Database."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"label": _("Customer Group"),
					"name": "Customer Group",
					"icon": "fa fa-sitemap",
					"link": "Tree/Customer Group",
					"description": _("Manage Customer Group Tree."),
				},
				{
					"type": "doctype",
					"name": "Lead Source",
					"description": _("Track Leads by Lead Source.")
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
					"name": "Item Attribute",
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
			"label": _("Price List"),
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
					"onboard": 1
				},
				{
					"type": "doctype",
					"label": _("Bulk Price Update"),
					"name": "Bulk Price Update",
					"description": _("Update or Upload Prices in Bulk."),
					"dependencies": ["Price List"],
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
					"name": "Price List Settings",
				},
			]
		},
		{
			"label": _("Special Prices"),
			"items": [
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
				{
					"type": "doctype",
					"name": "Coupon Code",
					"description": _("Define coupon codes."),
				},
				{
					"type": "doctype",
					"name": "Campaign",
					"description": _("Sales campaigns."),
				},
			]
		},
		{
			"label": _("Sales Persons & Territories"),
			"items": [
				{
					"type": "doctype",
					"label": _("Sales Person"),
					"name": "Sales Person",
					"icon": "fa fa-sitemap",
					"link": "Tree/Sales Person",
					"description": _("Manage Sales Person Tree."),
				},
				{
					"type": "doctype",
					"label": _("Territory"),
					"name": "Territory",
					"icon": "fa fa-sitemap",
					"link": "Tree/Territory",
					"description": _("Manage Territory Tree."),
				},
				{
					"type": "report",
					"is_query_report": True,
					"label": _("Sales Person Target Variance"),
					"name": "Sales Person Target Variance Based On Item Group",
					"route": "#query-report/Sales Person Target Variance Based On Item Group",
					"doctype": "Sales Person",
					"dependencies": ["Sales Person"],
				},
				{
					"type": "report",
					"is_query_report": True,
					"label": _("Territory Target Variance"),
					"name": "Territory Target Variance Based On Item Group",
					"route": "#query-report/Territory Target Variance Based On Item Group",
					"doctype": "Territory",
					"dependencies": ["Territory"],
				},
				{
					"type": "report",
					"is_query_report": True,
					"label": _("Sales Person Commission Summary"),
					"name": "Sales Person Commission Summary",
					"doctype": "Sales Person",
					"dependencies": ["Sales Person"],
				},
			]
		},
		{
			"label": _("External Sales Partners"),
			"items": [
				{
					"type": "doctype",
					"name": "Sales Partner",
					"description": _("Manage Sales Partners."),
				},
				{
					"type": "report",
					"is_query_report": True,
					"label": _("Sales Partner Target Variance"),
					"name": "Sales Partner Target Variance based on Item Group",
					"route": "#query-report/Sales Partner Target Variance based on Item Group",
					"doctype": "Sales Partner",
					"dependencies": ["Sales Partner"],
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Sales Partners Commission",
					"doctype": "Customer"
				}
			]
		},
		{
			"label": _("Key Reports"),
			"icon": "fa fa-table",
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Sales Analytics",
					"onboard": 1,
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Sales Details",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Customer Credit Balance",
					"doctype": "Customer"
				},
				{
					"type": "page",
					"name": "sales-funnel",
					"label": _("Sales Funnel"),
					"icon": "fa fa-bar-chart",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Sales Order Items To Be Delivered",
					"doctype": "Sales Order"
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
					"name": "Lead Details",
					"doctype": "Lead"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Address And Contacts",
					"label": _("Customer Addresses And Contacts"),
					"doctype": "Address",
					"route_options": {
						"party_type": "Customer"
					}
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Customers Without Any Sales Transactions",
					"doctype": "Customer"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Customer Acquisition and Loyalty",
					"doctype": "Customer",
					"icon": "fa fa-bar-chart",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Inactive Customers",
				},
			]
		},
		{
			"label": _("Settings"),
			"icon": "fa fa-cog",
			"items": [
				{
					"type": "doctype",
					"name": "Selling Settings",
					"description": _("Default settings for selling transactions."),
					"settings": 1,
				},
				{
					"type": "doctype",
					"name":"Terms and Conditions",
					"label": _("Terms and Conditions Template"),
					"description": _("Template of terms or contract."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Sales Taxes and Charges Template",
					"description": _("Tax template for selling transactions."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Transaction Type",
					"route_options": {
						"selling": 1
					}
				},
				{
					"type": "doctype",
					"name": "Sales Commission Category",
				},
			]
		},
	]

	return out
