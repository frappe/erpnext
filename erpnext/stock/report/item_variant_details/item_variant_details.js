// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Item Variant Details"] = {
	filters: [
		{
			reqd: 1,
			options: "Item",
			label: __("Items"),
			fieldname: "item",
			fieldtype: "MultiSelectList",
			get_data: (txt) => erpnext.utils.get_link_options("Item", txt, { has_variants: 1 }),
		},
		{
			fieldname: "warehouse",
			label: __("Warehouses"),
			fieldtype: "MultiSelectList",
			options: "Warehouse",
			get_data: (txt) => erpnext.utils.get_link_options("Warehouse", txt),
		},
	],
	tree: true,
	parent_field: "template",
};
