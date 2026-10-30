// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Item Variant Details"] = {
	filters: [
		{
			options: "Item",
			label: __("Items"),
			fieldname: "item",
			fieldtype: "MultiSelectList",
			get_data: (txt) => erpnext.utils.get_link_options("Item", txt, { has_variants: 1 }),
		},
		{
			fieldname: "item_group",
			label: __("Item Groups"),
			fieldtype: "MultiSelectList",
			options: "Item Group",
			get_data: (txt) => erpnext.utils.get_link_options("Item Group", txt),
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
