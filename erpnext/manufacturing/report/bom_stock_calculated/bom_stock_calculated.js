// Copyright (c) 2016, Epoch Consulting and contributors
// For license information, please see license.txt

frappe.query_reports["BOM Stock Calculated"] = {
	filters: [
		{
			fieldname: "bom",
			label: __("BOM"),
			fieldtype: "Link",
			options: "BOM",
			reqd: 1,
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
		},
		{
			fieldname: "qty_to_make",
			label: __("Quantity to Make"),
			fieldtype: "Float",
			default: "1.0",
			reqd: 1,
		},
		{
			fieldname: "show_exploded_view",
			label: __("Show exploded view"),
			fieldtype: "Check",
			default: false,
		},
	],
};
