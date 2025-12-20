// Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and Contributors and contributors
// For license information, please see license.txt

frappe.query_reports["BOM Search"] = {
	filters: [
		{
			fieldname: "item1",
			label: __("Item 1"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "item2",
			label: __("Item 2"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "item3",
			label: __("Item 3"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "item4",
			label: __("Item 4"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "item5",
			label: __("Item 5"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "search_sub_assemblies",
			label: __("Search Sub Assemblies"),
			fieldtype: "Check",
		},
	],
};
