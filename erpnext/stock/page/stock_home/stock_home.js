// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt"

frappe.module_page["Stock"] = [
	{
		title: frappe._("Documents"),
		top: true,
		icon: "icon-copy",
		items: [
			{
				label: frappe._("Item"),
				description: frappe._("All Products or Services."),
				doctype: "Item"
			},
			{
				label: frappe._("Material Request"),
				description: frappe._("Requests for items."),
				doctype: "Material Request"
			},
			{
				label: frappe._("Stock Entry"),
				description: frappe._("Record item movement."),
				doctype: "Stock Entry"
			},
			{
				label: frappe._("Delivery Note"),
				description: frappe._("Shipments to customers."),
				doctype: "Delivery Note"
			},
			{
				label: frappe._("Purchase Receipt"),
				description: frappe._("Goods received from Suppliers."),
				doctype: "Purchase Receipt"
			},
		]
	},
	{
		title: frappe._("Masters"),
		icon: "icon-book",
		items: [
			{
				label: frappe._("Serial No"),
				description: frappe._("Single unit of an Item."),
				doctype: "Serial No"
			},
			{
				label: frappe._("Batch"),
				description: frappe._("Batch (lot) of an Item."),
				doctype: "Batch"
			},
			{
				label: frappe._("Warehouse"),
				description: frappe._("Where items are stored."),
				doctype: "Warehouse"
			},
		]
	},
	{
		title: frappe._("Tools"),
		icon: "icon-wrench",
		items: [
			{
				doctype: "Stock Reconciliation",
				label: frappe._("Stock Reconciliation"),
				description: frappe._("Upload stock balance via csv.")
			},
			{
				doctype: "Installation Note",
				label: frappe._("Installation Note"),
				description: frappe._("Installation record for a Serial No.")
			},
			{
				label: frappe._("Packing Slip"),
				doctype: "Packing Slip",
				description: frappe._("Split Delivery Note into packages.")
			},
			{
				doctype: "Price List",
				label: frappe._("Price List"),
				description: frappe._("Multiple Price list.")
			},
			{
				doctype: "Item Price",
				label: frappe._("Item Price"),
				description: frappe._("Multiple Item prices.")
			},
			{
				doctype: "Quality Inspection",
				label: frappe._("Quality Inspection"),
				description: frappe._("Incoming quality inspection.")
			},
			{
				route: "Form/Landed Cost Wizard/Landed Cost Wizard",
				label: frappe._("Landed Cost Wizard"),
				description: frappe._("Distribute transport overhead across items."),
				doctype: "Landed Cost Wizard"
			},
			{
				route: "Form/Stock UOM Replace Utility/Stock UOM Replace Utility",
				label: frappe._("UOM Replace Utility"),
				description: frappe._("Change UOM for an Item."),
				doctype: "Stock UOM Replace Utility"
			},
		]
	},
	{
		title: frappe._("Setup"),
		icon: "icon-cog",
		items: [
			{
				label: frappe._("Stock Settings"),
				route: "Form/Stock Settings",
				doctype: "Stock Settings",
				description: frappe._("Settings for Stock Module")
			},
			{
				route: "Sales Browser/Item Group",
				label: frappe._("Item Group"),
				doctype: "Item Group",
				description: frappe._("Item classification.")
			},
			{
				doctype: "UOM",
				label: frappe._("Unit of Measure") + " (UOM)",
				description: frappe._("e.g. Kg, Unit, Nos, m")
			},
			{
				doctype: "Brand",
				label: frappe._("Brand"),
				description: frappe._("Brand master.")
			}
		]
	},
	{
		title: frappe._("Main Reports"),
		right: true,
		icon: "icon-table",
		items: [
			{
				label: frappe._("Stock Ledger"),
				doctype: "Item",
				route: "query-report/Stock Ledger"
			},
			{
				label: frappe._("Stock Balance"),
				page: "stock-balance"
			},
			{
				label: frappe._("Stock Projected Qty"),
				doctype: "Item",
				route: "query-report/Stock Projected Qty"
			},
			{
				label: frappe._("Stock Ageing"),
				doctype: "Item",
				route: "query-report/Stock Ageing"
			},
			{
				label: frappe._("Item-wise Price List Rate"),
				route: "Report/Item Price/Item-wise Price List Rate",
				doctype: "Item Price"
			},
		]
	},
	{
		title: frappe._("Analytics"),
		right: true,
		icon: "icon-bar-chart",
		items: [
			{
				label: frappe._("Stock Analytics"),
				page: "stock-analytics"
			},
		]
	},
	{
		title: frappe._("Reports"),
		right: true,
		icon: "icon-list",
		items: [
			{
				label: frappe._("Ordered Items To Be Delivered"),
				route: "query-report/Ordered Items To Be Delivered",
				doctype: "Delivery Note"
			},
			{
				label: frappe._("Purchase Order Items To Be Received"),
				route: "query-report/Purchase Order Items To Be Received",
				doctype: "Purchase Receipt"
			},
			{
				label: frappe._("Item Shortage Report"),
				route: "Report/Bin/Item Shortage Report",
				doctype: "Purchase Receipt"
			},
			{
				label: frappe._("Serial No Service Contract Expiry"),
				route: "Report/Serial No/Serial No Service Contract Expiry",
				doctype: "Serial No"
			},
			{
				label: frappe._("Serial No Status"),
				route: "Report/Serial No/Serial No Status",
				doctype: "Serial No"
			},
			{
				label: frappe._("Serial No Warranty Expiry"),
				route: "Report/Serial No/Serial No Warranty Expiry",
				doctype: "Serial No"
			},
			{
				label: frappe._("Purchase In Transit"),
				route: "query-report/Purchase In Transit",
				doctype: "Purchase Order"
			},
			{
				label: frappe._("Requested Items To Be Transferred"),
				route: "query-report/Requested Items To Be Transferred",
				doctype: "Material Request"
			},
			{
				label: frappe._("Batch-Wise Balance History"),
				route: "query-report/Batch-Wise Balance History",
				doctype: "Batch"
			},
			{
				label: frappe._("Warehouse-Wise Stock Balance"),
				route: "query-report/Warehouse-Wise Stock Balance",
				doctype: "Warehouse"
			},
			{
				label: frappe._("Item Prices"),
				route: "query-report/Item Prices",
				doctype: "Price List"
			},
			{
				label: frappe._("Itemwise Recommended Reorder Level"),
				route: "query-report/Itemwise Recommended Reorder Level",
				doctype: "Item"
			},
			{
				label: frappe._("Delivery Note Trends"),
				route: "query-report/Delivery Note Trends",
				doctype: "Delivery Note"
			},
			{
				label: frappe._("Purchase Receipt Trends"),
				route: "query-report/Purchase Receipt Trends",
				doctype: "Purchase Receipt"
			},
		]
	}
]

pscript['onload_stock-home'] = function(wrapper) {
	frappe.views.moduleview.make(wrapper, "Stock");
}