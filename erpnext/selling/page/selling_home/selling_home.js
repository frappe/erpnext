// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt"

frappe.module_page["Selling"] = [
	{
		top: true,
		title: frappe._("Documents"),
		icon: "icon-copy",
		items: [
			{
				label: frappe._("Customer"),
				description: frappe._("Customer database."),
				doctype:"Customer"
			},
			{
				label: frappe._("Lead"),
				description: frappe._("Database of potential customers."),
				doctype:"Lead"
			},
			{
				label: frappe._("Opportunity"),
				description: frappe._("Potential opportunities for selling."),
				doctype:"Opportunity"
			},
			{
				label: frappe._("Quotation"),
				description: frappe._("Quotes to Leads or Customers."),
				doctype:"Quotation"
			},
			{
				label: frappe._("Sales Order"),
				description: frappe._("Confirmed orders from Customers."),
				doctype:"Sales Order"
			},
		]
	},
	{
		title: frappe._("Masters"),
		icon: "icon-book",
		items: [
			{
				label: frappe._("Contact"),
				description: frappe._("All Contacts."),
				doctype:"Contact"
			},
			{
				label: frappe._("Address"),
				description: frappe._("All Addresses."),
				doctype:"Address"
			},
			{
				label: frappe._("Item"),
				description: frappe._("All Products or Services."),
				doctype:"Item"
			},
		]
	},
	{
		title: frappe._("Setup"),
		icon: "icon-cog",
		items: [
			{
				"label": frappe._("Selling Settings"),
				"route": "Form/Selling Settings",
				"doctype":"Selling Settings",
				"description": frappe._("Settings for Selling Module")
			},
			{
				label: frappe._("Sales Taxes and Charges Master"),
				description: frappe._("Sales taxes template."),
				doctype:"Sales Taxes and Charges Master"
			},
			{
				label: frappe._("Shipping Rules"),
				description: frappe._("Rules to calculate shipping amount for a sale"),
				doctype:"Shipping Rule"
			},
			{
				label: frappe._("Price List"),
				description: frappe._("Multiple Price list."),
				doctype:"Price List"
			},
			{
				label: frappe._("Item Price"),
				description: frappe._("Multiple Item prices."),
				doctype:"Item Price"
			},
			{
				label: frappe._("Sales BOM"),
				description: frappe._("Bundle items at time of sale."),
				doctype:"Sales BOM"
			},
			{
				label: frappe._("Terms and Conditions"),
				description: frappe._("Template of terms or contract."),
				doctype:"Terms and Conditions"
			},
			{
				label: frappe._("Customer Group"),
				description: frappe._("Customer classification tree."),
				route: "Sales Browser/Customer Group",
				doctype:"Customer Group"
			},
			{
				label: frappe._("Territory"),
				description: frappe._("Sales territories."),
				route: "Sales Browser/Territory",
				doctype:"Territory"
			},
			{
				"route":"Sales Browser/Sales Person",
				"label":frappe._("Sales Person"),
				"description": frappe._("Sales persons and targets"),
				doctype:"Sales Person"
			},
			{
				"route":"List/Sales Partner",
				"label": frappe._("Sales Partner"),
				"description":frappe._("Commission partners and targets"),
				doctype:"Sales Partner"
			},
			{
				"route":"Sales Browser/Item Group",
				"label":frappe._("Item Group"),
				"description": frappe._("Tree of item classification"),
				doctype:"Item Group"
			},
			{
				"route":"List/Campaign",
				"label":frappe._("Campaign"),
				"description":frappe._("Sales campaigns"),
				doctype:"Campaign"
			},
		]
	},
	{
		title: frappe._("Tools"),
		icon: "icon-wrench",
		items: [
			{
				"route":"Form/SMS Center/SMS Center",
				"label":frappe._("SMS Center"),
				"description":frappe._("Send mass SMS to your contacts"),
				doctype:"SMS Center"
			},
		]
	},
	{
		title: frappe._("Analytics"),
		right: true,
		icon: "icon-bar-chart",
		items: [
			{
				"label":frappe._("Sales Analytics"),
				page: "sales-analytics"
			},
			{
				"label":frappe._("Sales Funnel"),
				page: "sales-funnel"
			},
			{
				"label":frappe._("Customer Acquisition and Loyalty"),
				route: "query-report/Customer Acquisition and Loyalty",
				doctype: "Customer"
			},
		]
	},
	{
		title: frappe._("Reports"),
		right: true,
		icon: "icon-list",
		items: [
			{
				"label":frappe._("Lead Details"),
				route: "query-report/Lead Details",
				doctype: "Lead"
			},
			{
				"label":frappe._("Customer Addresses And Contacts"),
				route: "query-report/Customer Addresses And Contacts",
				doctype: "Contact"
			},
			{
				"label":frappe._("Ordered Items To Be Delivered"),
				route: "query-report/Ordered Items To Be Delivered",
				doctype: "Sales Order"
			},
			{
				"label":frappe._("Sales Person-wise Transaction Summary"),
				route: "query-report/Sales Person-wise Transaction Summary",
				doctype: "Sales Order"
			},
			{
				"label":frappe._("Item-wise Sales History"),
				route: "query-report/Item-wise Sales History",
				doctype: "Item"
			},
			{
				"label":frappe._("Territory Target Variance (Item Group-Wise)"),
				route: "query-report/Territory Target Variance Item Group-Wise",
				doctype: "Territory"
			},
			{
				"label":frappe._("Sales Person Target Variance (Item Group-Wise)"),
				route: "query-report/Sales Person Target Variance Item Group-Wise",
				doctype: "Sales Person",
			},
			{
				"label":frappe._("Customers Not Buying Since Long Time"),
				route: "query-report/Customers Not Buying Since Long Time",
				doctype: "Sales Order"
			},
			{
				"label":frappe._("Quotation Trend"),
				route: "query-report/Quotation Trends",
				doctype: "Quotation"
			},
			{
				"label":frappe._("Sales Order Trend"),
				route: "query-report/Sales Order Trends",
				doctype: "Sales Order"
			},
			{
				"label":frappe._("Available Stock for Packing Items"),
				route: "query-report/Available Stock for Packing Items",
				doctype: "Item",
			},
			{
				"label":frappe._("Pending SO Items For Purchase Request"),
				route: "query-report/Pending SO Items For Purchase Request",
				doctype: "Sales Order"
			},
		]
	}
]

pscript['onload_selling-home'] = function(wrapper) {
	frappe.views.moduleview.make(wrapper, "Selling");
}