// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Batch Split Tree"] = {
	filters: [
		{
			fieldname: "batch",
			label: __("Parent Batch"),
			fieldtype: "Link",
			options: "Batch",
		},
		{
			fieldname: "item_code",
			label: __("Item Code"),
			fieldtype: "Link",
			options: "Item",
		},
	],
	initial_depth: 5,
};
