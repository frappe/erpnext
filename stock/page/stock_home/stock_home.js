// ERPNext: Copyright 2013 Web Notes Technologies Pvt Ltd
// GNU General Public License. See "license.txt"

wn.module_page["Stock"] = [
	{
		title: wn._("Documents"),
		icon: "icon-copy",
		items: [
			{
				label: wn._("Material Request"),
				description: wn._("Request Material for Transfer or Purchase."),
				doctype:"Material Request"
			},
			{
				label: wn._("Stock Entry"),
				description: wn._("Transfer stock from one warehouse to another."),
				doctype:"Stock Entry"
			},
			{
				label: wn._("Delivery Note"),
				description: wn._("Delivery (shipment) to customers."),
				doctype:"Delivery Note"
			},
			{
				label: wn._("Purchase Receipt"),
				description: wn._("Goods received from Suppliers."),
				doctype:"Purchase Receipt"
			},
		]
	},
	{
		title: wn._("Masters"),
		icon: "icon-book",
		items: [
			{
				label: wn._("Item"),
				description: wn._("All Products or Services."),
				doctype:"Item"
			},
			{
				label: wn._("Serial No"),
				description: wn._("Single unit of an Item."),
				doctype:"Serial No"
			},
			{
				label: wn._("Batch"),
				description: wn._("Batch (lot) of an Item."),
				doctype:"Batch"
			},
			{
				label: wn._("Warehouse"),
				description: wn._("Where items are stored."),
				doctype:"Warehouse"
			},
		]
	},
	{
		title: wn._("Tools"),
		icon: "icon-wrench",
		items: [
			{
				"doctype":"Stock Reconciliation",
				"label": wn._("Stock Reconciliation"),
				description: wn._("Upload stock balance via csv.")
			},
			{
				"doctype":"Installation Note",
				"label": wn._("Installation Note"),
				description: wn._("Installation record for a Serial No.")
			},
			{
				"label": wn._("Packing Slip"),
				"doctype":"Packing Slip",
				description: wn._("Split Delivery Note into packages.")
			},
			{
				"doctype":"Price List",
				"label": wn._("Price List"),
				"description": wn._("Multiple Item Prices")
			},
			{
				"doctype":"Quality Inspection",
				"label": wn._("Quality Inspection"),
				description: wn._("Incoming quality inspection.")
			},
			{
				"route":"Form/Landed Cost Wizard/Landed Cost Wizard",
				"label": wn._("Landed Cost Wizard"),
				description: wn._("Distribute transport overhead across items."),
				doctype: "Landed Cost Wizard"
			},
			{
				"route":"Form/Stock UOM Replace Utility/Stock UOM Replace Utility",
				"label": wn._("UOM Replace Utility"),
				description: wn._("Change UOM for an Item."),
				"doctype": "Stock UOM Replace Utility"
			},
		]
	},
	{
		title: wn._("Setup"),
		icon: "icon-cog",
		items: [
			{
				"route":"Sales Browser/Item Group",
				"label": wn._("Item Group"),
				"description": wn._("Item classification.")
			},
			{
				"doctype":"UOM",
				"label": wn._("Unit of Measure") + " (UOM)",
				"description": wn._("e.g. Kg, Unit, Nos, m")
			},
			{
				"doctype":"Brand",
				"label": wn._("Brand"),
				"description": wn._("Brand master.")
			},
			{
				"label": wn._("Warehouse Type"),
				"doctype":"Warehouse Type",
				"description": wn._("Types of warehouse")
			}
		]
	},
	{
		title: wn._("Main Reports"),
		right: true,
		icon: "icon-table",
		items: [
			{
				"label":wn._("Stock Ledger"),
				page: "stock-ledger"
			},
			{
				"label":wn._("Stock Balance"),
				page: "stock-balance"
			},
			{
				"page":"stock-level",
				"label": wn._("Stock Level")
			},
			{
				"page":"stock-ageing",
				"label": wn._("Stock Ageing")
			},
		]
	},
	{
		title: wn._("Analytics"),
		right: true,
		icon: "icon-bar-chart",
		items: [
			{
				"label":wn._("Stock Analytics"),
				page: "stock-analytics"
			},
		]
	},
	{
		title: wn._("Reports"),
		right: true,
		icon: "icon-list",
		items: [
			{
				"label":wn._("Stock Ledger"),
				route: "Report2/Stock Ledger Entry/Stock Ledger",
				doctype: "Stock Ledger Entry"
			},
			{
				"label":wn._("Ordered Items To Be Delivered"),
				route: "query-report/Ordered Items To Be Delivered",
				doctype: "Delivery Note"
			},
			{
				"label":wn._("Purchase Order Items To Be Received"),
				route: "query-report/Purchase Order Items To Be Received",
				doctype: "Purchase Receipt"
			},
			{
				"label":wn._("Serial No Service Contract Expiry"),
				route: "Report2/Serial No/Serial No Service Contract Expiry",
				doctype: "Serial No"
			},
			{
				"label":wn._("Serial No Status"),
				route: "Report2/Serial No/Serial No Status",
				doctype: "Serial No"
			},
			{
				"label":wn._("Serial No Warranty Expiry"),
				route: "Report2/Serial No/Serial No Warranty Expiry",
				doctype: "Serial No"
			},
			{
				"label":wn._("Item-Wise Price List"),
				route: "query-report/Item-Wise Price List",
				doctype: "Item"
			},
			{
				"label":wn._("Purchase In Transit"),
				route: "query-report/Purchase In Transit",
			},
			{
				"label":wn._("Requested Items To Be Transferred"),
				route: "query-report/Requested Items To Be Transferred",
			},
			{
				"label":wn._("Batch-Wise Balance History"),
				route: "query-report/Batch-Wise Balance History",
			},
			{
				"label":wn._("Warehouse-Wise Stock Balance"),
				route: "query-report/Warehouse-Wise Stock Balance",
			},
			{
				"label":wn._("Item Prices"),
				route: "query-report/Item Prices",

			},
			{
				"label":wn._("Itemwise Recommended Reorder Level"),
				route: "query-report/Itemwise Recommended Reorder Level",
				doctype: "Item"
			},
			{
				"label":wn._("Delivery Note Trends"),
				route: "query-report/Delivery Note Trends",
				doctype: "Delivery Note"
			},
			{
				"label":wn._("Purchase Receipt Trends"),
				route: "query-report/Purchase Receipt Trends",
				doctype: "Purchase Receipt"
			},
		]
	}
]

pscript['onload_stock-home'] = function(wrapper) {
	wn.views.moduleview.make(wrapper, "Stock");
}