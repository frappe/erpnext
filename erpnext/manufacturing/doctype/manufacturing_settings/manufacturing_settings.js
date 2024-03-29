// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Manufacturing Settings", {});

frappe.tour["Manufacturing Settings"] = [
	{
		fieldname: "material_consumption",
		title: __("Allow Multiple Material Consumption"),
		description: __(
			"If ticked, multiple materials can be used for a single Work Order. This is useful if one or more time consuming products are being manufactured."
		),
	},
	{
		fieldname: "backflush_raw_materials_based_on",
		title: __("Backflush Raw Materials"),
		description: __(
			"The Stock Entry of type 'Manufacture' is known as backflush. Raw materials being consumed to manufacture finished goods is known as backflushing. <br><br> When creating Manufacture Entry, raw-material items are backflushed based on BOM of production item. If you want raw-material items to be backflushed based on Material Transfer entry made against that Work Order instead, then you can set it under this field."
		),
	},
	{
		fieldname: "default_wip_warehouse",
		title: __("Work In Progress Warehouse"),
		description: __(
			"This Warehouse will be auto-updated in the Work In Progress Warehouse field of Work Orders."
		),
	},
	{
		fieldname: "default_fg_warehouse",
		title: __("Finished Goods Warehouse"),
		description: __("This Warehouse will be auto-updated in the Target Warehouse field of Work Order."),
	},
	{
		fieldname: "update_bom_costs_automatically",
		title: __("Update BOM Cost Automatically"),
		description: __(
			"If ticked, the BOM cost will be automatically updated based on Valuation Rate / Price List Rate / last purchase rate of raw materials."
		),
	},
];
