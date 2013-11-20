// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt"

wn.module_page["Selling"] = [
	{
		top: true,
		title: wn._("Documents"),
		icon: "icon-copy",
		items: [
			{
				label: wn._("Customer"),
				description: wn._("Customer database."),
				doctype:"Customer"
			},
			{
				label: wn._("Lead"),
				description: wn._("Database of potential customers."),
				doctype:"Lead"
			},
			{
				label: wn._("Opportunity"),
				description: wn._("Potential opportunities for selling."),
				doctype:"Opportunity"
			},
			{
				label: wn._("Quotation"),
				description: wn._("Quotes to Leads or Customers."),
				doctype:"Quotation"
			},
			{
				label: wn._("Sales Order"),
				description: wn._("Confirmed orders from Customers."),
				doctype:"Sales Order"
			},
		]
	},
	{
		title: wn._("Masters"),
		icon: "icon-book",
		items: [
			{
				label: wn._("Contact"),
				description: wn._("All Contacts."),
				doctype:"Contact"
			},
			{
				label: wn._("Address"),
				description: wn._("All Addresses."),
				doctype:"Address"
			},
			{
				label: wn._("Item"),
				description: wn._("All Products or Services."),
				doctype:"Item"
			},
		]
	},
	{
		title: wn._("Setup"),
		icon: "icon-cog",
		items: [
			{
				"label": wn._("Selling Settings"),
				"route": "Form/Selling Settings",
				"doctype":"Selling Settings",
				"description": wn._("Settings for Selling Module")
			},
			{
				"route":"Form/Shopping Cart Settings",
				"label":wn._("Shopping Cart Settings"),
				"description":wn._("Setup of Shopping Cart."),
				doctype:"Shopping Cart Settings"
			},
			{
				label: wn._("Sales Taxes and Charges Master"),
				description: wn._("Sales taxes template."),
				doctype:"Sales Taxes and Charges Master"
			},
			{
				label: wn._("Shipping Rules"),
				description: wn._("Rules to calculate shipping amount for a sale"),
				doctype:"Shipping Rule"
			},
			{
				label: wn._("Price List"),
				description: wn._("Multiple Price list."),
				doctype:"Price List"
			},
			{
				label: wn._("Item Price"),
				description: wn._("Multiple Item prices."),
				doctype:"Item Price"
			},
			{
				label: wn._("Sales BOM"),
				description: wn._("Bundle items at time of sale."),
				doctype:"Sales BOM"
			},
			{
				label: wn._("Terms and Conditions"),
				description: wn._("Template of terms or contract."),
				doctype:"Terms and Conditions"
			},
			{
				label: wn._("Customer Group"),
				description: wn._("Customer classification tree."),
				route: "Sales Browser/Customer Group",
				doctype:"Customer Group"
			},
			{
				label: wn._("Territory"),
				description: wn._("Sales territories."),
				route: "Sales Browser/Territory",
				doctype:"Territory"
			},
			{
				"route":"Sales Browser/Sales Person",
				"label":wn._("Sales Person"),
				"description": wn._("Sales persons and targets"),
				doctype:"Sales Person"
			},
			{
				"route":"List/Sales Partner",
				"label": wn._("Sales Partner"),
				"description":wn._("Commission partners and targets"),
				doctype:"Sales Partner"
			},
			{
				"route":"Sales Browser/Item Group",
				"label":wn._("Item Group"),
				"description": wn._("Tree of item classification"),
				doctype:"Item Group"
			},
			{
				"route":"List/Campaign",
				"label":wn._("Campaign"),
				"description":wn._("Sales campaigns"),
				doctype:"Campaign"
			},
		]
	},
	{
		title: wn._("Tools"),
		icon: "icon-wrench",
		items: [
			{
				"route":"Form/SMS Center/SMS Center",
				"label":wn._("SMS Center"),
				"description":wn._("Send mass SMS to your contacts"),
				doctype:"SMS Center"
			},
		]
	},
	{
		title: wn._("Analytics"),
		right: true,
		icon: "icon-bar-chart",
		items: [
			{
				"label":wn._("Sales Analytics"),
				page: "sales-analytics"
			},
			{
				"label":wn._("Sales Funnel"),
				page: "sales-funnel"
			},
		]
	},
	{
		title: wn._("Reports"),
		right: true,
		icon: "icon-list",
		items: [
			{
				"label":wn._("Lead Details"),
				route: "query-report/Lead Details",
				doctype: "Lead"
			},
			{
				"label":wn._("Customer Addresses And Contacts"),
				route: "query-report/Customer Addresses And Contacts",
				doctype: "Contact"
			},
			{
				"label":wn._("Ordered Items To Be Delivered"),
				route: "query-report/Ordered Items To Be Delivered",
				doctype: "Sales Order"
			},
			{
				"label":wn._("Sales Person-wise Transaction Summary"),
				route: "query-report/Sales Person-wise Transaction Summary",
				doctype: "Sales Order"
			},
			{
				"label":wn._("Item-wise Sales History"),
				route: "query-report/Item-wise Sales History",
				doctype: "Item"
			},
			{
				"label":wn._("Territory Target Variance (Item Group-Wise)"),
				route: "query-report/Territory Target Variance Item Group-Wise",
				doctype: "Territory"
			},
			{
				"label":wn._("Sales Person Target Variance (Item Group-Wise)"),
				route: "query-report/Sales Person Target Variance Item Group-Wise",
				doctype: "Sales Person",
			},
			{
				"label":wn._("Customers Not Buying Since Long Time"),
				route: "query-report/Customers Not Buying Since Long Time",
				doctype: "Sales Order"
			},
			{
				"label":wn._("Quotation Trend"),
				route: "query-report/Quotation Trends",
				doctype: "Quotation"
			},
			{
				"label":wn._("Sales Order Trend"),
				route: "query-report/Sales Order Trends",
				doctype: "Sales Order"
			},
			{
				"label":wn._("Available Stock for Packing Items"),
				route: "query-report/Available Stock for Packing Items",
				doctype: "Item",
			},
			{
				"label":wn._("Pending SO Items For Purchase Request"),
				route: "query-report/Pending SO Items For Purchase Request",
				doctype: "Sales Order"
			},
		]
	}
]

pscript['onload_selling-home'] = function(wrapper) {
	wn.views.moduleview.make(wrapper, "Selling");
}