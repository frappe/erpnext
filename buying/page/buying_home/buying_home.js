// ERPNext: Copyright 2013 Web Notes Technologies Pvt Ltd
// GNU General Public License. See "license.txt"

wn.module_page["Buying"] = [
	{
		title: wn._("Documents"),
		icon: "icon-copy",
		items: [
			{
				label: wn._("Material Request"),
				description: wn._("Request for purchase."),
				doctype:"Material Request"
			},
			{
				label: wn._("Supplier Quotation"),
				description: wn._("Track Quotations received from Suppliers."),
				doctype:"Supplier Quotation"
			},
			{
				label: wn._("Purchase Order"),
				description: wn._("Purchase Orders given to Suppliers."),
				doctype:"Purchase Order"
			},
		]
	},
	{
		title: wn._("Masters"),
		icon: "icon-book",
		items: [
		{
			label: wn._("Supplier"),
			description: wn._("Supplier database."),
			doctype:"Supplier"
		},
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
				"label": wn._("Purchase Taxes and Charges Master"),
				"doctype":"Purchase Taxes and Charges Master",
				"description": wn._("Tax Template for Purchase")
			},
			{
				"doctype":"Supplier Type",
				"label": wn._("Supplier Type"),
				"description": wn._("Supplier classification.")
			},
			{
				"route":"Sales Browser/Item Group",
				"label":wn._("Item Group"),
				"description": wn._("Tree of item classification"),
				doctype:"Item Group"
			},
			{
				label: wn._("Terms and Conditions"),
				description: wn._("Template of terms or contract."),
				doctype:"Terms and Conditions"
			},
		]
	},
	{
		title: wn._("Tools"),
		icon: "icon-wrench",
		items: [
		]
	},
	{
		title: wn._("Analytics"),
		right: true,
		icon: "icon-bar-chart",
		items: [
			{
				"label":wn._("Purchase Analytics"),
				page: "purchase-analytics"
			},
		]
	},
	{
		title: wn._("Reports"),
		right: true,
		icon: "icon-list",
		items: [
			{
				"label":wn._("Item-wise Purchase History"),
				route: "query-report/Item-wise Purchase History",
			},
			{
				"label":wn._("Purchase In Transit"),
				route: "query-report/Purchase In Transit",
			},
			{
				"label":wn._("Requested Items To Be Ordered"),
				route: "query-report/Requested Items To Be Ordered",
			},
			{
				"label":wn._("Purchase Order Trends"),
				route: "query-report/Purchase Order Trends",
				doctype: "Purchase Order"
			},
			{
				"label":wn._("Item-wise Last Purchase Rate"),
				route: "query-report/Item-wise Last Purchase Rate",
			}
		]
	}
]

pscript['onload_buying-home'] = function(wrapper) {
	wn.views.moduleview.make(wrapper, "Buying");
}
