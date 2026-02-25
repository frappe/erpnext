// Copyright (c) 2016, Hash Include Solutions FZC and contributors
// For license information, please see license.txt

frappe.query_reports["Item Price Stock"] = {
	filters: [
		{
			fieldname: "item_code",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
		},
	],
};
