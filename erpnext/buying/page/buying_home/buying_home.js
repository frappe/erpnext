// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt"

frappe.module_page["Buying"] = [
	{
		title: frappe._("Documents"),
		top: true,
		icon: "icon-copy",
		items: [
			{
				label: frappe._("Supplier"),
				description: frappe._("Supplier database."),
				doctype:"Supplier"
			},
			{
				label: frappe._("Material Request"),
				description: frappe._("Request for purchase."),
				doctype:"Material Request"
			},
			{
				label: frappe._("Supplier Quotation"),
				description: frappe._("Quotations received from Suppliers."),
				doctype:"Supplier Quotation"
			},
			{
				label: frappe._("Purchase Order"),
				description: frappe._("Purchase Orders given to Suppliers."),
				doctype:"Purchase Order"
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
				"label": frappe._("Buying Settings"),
				"route": "Form/Buying Settings",
				"doctype":"Buying Settings",
				"description": frappe._("Settings for Buying Module")
			},
			{
				"label": frappe._("Purchase Taxes and Charges Master"),
				"doctype":"Purchase Taxes and Charges Master",
				"description": frappe._("Tax Template for Purchase")
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
				"doctype":"Supplier Type",
				"label": frappe._("Supplier Type"),
				"description": frappe._("Supplier classification.")
			},
			{
				"route":"Sales Browser/Item Group",
				"label":frappe._("Item Group"),
				"description": frappe._("Tree of item classification"),
				doctype:"Item Group"
			},
			{
				label: frappe._("Terms and Conditions"),
				description: frappe._("Template of terms or contract."),
				doctype:"Terms and Conditions"
			},
		]
	},
	{
		title: frappe._("Tools"),
		icon: "icon-wrench",
		items: [
		]
	},
	{
		title: frappe._("Analytics"),
		right: true,
		icon: "icon-bar-chart",
		items: [
			{
				"label":frappe._("Purchase Analytics"),
				page: "purchase-analytics"
			},
		]
	},
	{
		title: frappe._("Reports"),
		right: true,
		icon: "icon-list",
		items: [
			{
				"label":frappe._("Items To Be Requested"),
				route: "query-report/Items To Be Requested",
				doctype: "Item"
			},
			{
				"label":frappe._("Requested Items To Be Ordered"),
				route: "query-report/Requested Items To Be Ordered",
				doctype: "Material Request"
			},
			{
				"label":frappe._("Material Requests for which Supplier Quotations are not created"),
				route: "query-report/Material Requests for which Supplier Quotations are not created",
				doctype: "Material Request"
			},
			{
				"label":frappe._("Purchase In Transit"),
				route: "query-report/Purchase In Transit",
				doctype: "Purchase Order"
			},
			{
				"label":frappe._("Item-wise Purchase History"),
				route: "query-report/Item-wise Purchase History",
				doctype: "Item"
			},
			{
				"label":frappe._("Item-wise Last Purchase Rate"),
				route: "query-report/Item-wise Last Purchase Rate",
				doctype: "Item"
			},
			{
				"label":frappe._("Purchase Order Trends"),
				route: "query-report/Purchase Order Trends",
				doctype: "Purchase Order"
			},
			{
				"label":frappe._("Supplier Addresses And Contacts"),
				route: "query-report/Supplier Addresses and Contacts",
				doctype: "Supplier"
			},
			{
				"label":frappe._("Supplier-Wise Sales Analytics"),
				route: "query-report/Supplier-Wise Sales Analytics",
				doctype: "Stock Ledger Entry"
			}
		]
	}
]

pscript['onload_buying-home'] = function(wrapper) {
	frappe.views.moduleview.make(wrapper, "Buying");
}
