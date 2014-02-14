// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt"

frappe.module_page["Manufacturing"] = [
	{
		title: frappe._("Documents"),
		top: true,
		icon: "icon-copy",
		items: [
			{
				label: frappe._("Bill of Materials"),
				description: frappe._("Bill of Materials (BOM)"),
				doctype:"BOM"
			},
			{
				label: frappe._("Production Order"),
				description: frappe._("Orders released for production."),
				doctype:"Production Order"
			},
		]
	},
	{
		title: frappe._("Production Planning (MRP)"),
		icon: "icon-wrench",
		items: [
			{
				"route":"Form/Production Planning Tool/Production Planning Tool",
				"label":frappe._("Production Planning Tool"),
				"description":frappe._("Generate Material Requests (MRP) and Production Orders."),
				doctype: "Production Planning Tool"
			},
		]
	},
	{
		title: frappe._("Masters"),
		icon: "icon-book",
		items: [
			{
				label: frappe._("Item"),
				description: frappe._("All Products or Services."),
				doctype:"Item"
			},
			{
				label: frappe._("Workstation"),
				description: frappe._("Where manufacturing operations are carried out."),
				doctype:"Workstation"
			},
		]
	},
	{
		title: frappe._("Utility"),
		icon: "icon-wrench",
		items: [
			{
				"route":"Form/BOM Replace Tool/BOM Replace Tool",
				"label":frappe._("BOM Replace Tool"),
				"description":frappe._("Replace Item / BOM in all BOMs"),
				doctype: "BOM Replace Tool"
			},
		]
	},
	{
		title: frappe._("Reports"),
		right: true,
		icon: "icon-list",
		items: [
			{
				"label":frappe._("Open Production Orders"),
				route: "query-report/Open Production Orders",
				doctype:"Production Order"
			},
			{
				"label":frappe._("Production Orders in Progress"),
				route: "query-report/Production Orders in Progress",
				doctype:"Production Order"
			},
			{
				"label":frappe._("Issued Items Against Production Order"),
				route: "query-report/Issued Items Against Production Order",
				doctype:"Production Order"
			},
			{
				"label":frappe._("Completed Production Orders"),
				route: "query-report/Completed Production Orders",
				doctype:"Production Order"
			},
		]
	}
]

pscript['onload_manufacturing-home'] = function(wrapper) {
	frappe.views.moduleview.make(wrapper, "Manufacturing");
}