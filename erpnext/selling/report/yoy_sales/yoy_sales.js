// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["YoY Sales"] = {
	"filters": [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options:"Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1
		},
		// {
		// 	fieldname: "item_group",
		// 	label: __("Item Group"),
		// 	fieldtype: "Link",
		// 	options:"Item Group",
		// 	default: "",
		// 	reqd: 0
		// },
		// {
		// 	fieldname: "item_code",
		// 	label: __("Item Code"),
		// 	fieldtype: "Link",
		// 	options:"Item",
		// 	default: "",
		// 	reqd: 0
		// },
		{
			"fieldname":"based_on",
			"label": __("Based On"),
			"fieldtype": "Select",
			"options": [
				{ "value": "Item", "label": __("Item") },
				{ "value": "Item Group", "label": __("Item Group") },
				{ "value": "Customer", "label": __("Customer") },
				{ "value": "Customer Group", "label": __("Customer Group") },
				{ "value": "Territory", "label": __("Territory") },
			],
			"default": "Item",
			"dashboard_config": {
				"read_only": 1,
			}
		},
		{
			fieldname: "from_year",
			label: __("From Year"),
			fieldtype: "Int",
			// options:["", "Item Group", "Customer", "Customer Group"],
			default: 2020,
			reqd: 1
		},
		{
			fieldname: "to_year",
			label: __("To Year"),
			fieldtype: "Int",
			// options:["", "Item Group", "Customer", "Customer Group"],
			default: 2022,
			reqd: 1
		},
		// {
		// 	"fieldname":"group_by",
		// 	"label": __("Group By"),
		// 	"fieldtype": "Select",
		// 	"options": [
		// 		"",
		// 		{ "value": "Item", "label": __("Item") },
		// 		{ "value": "Customer", "label": __("Customer") }
		// 	],
		// 	"default": ""
		// },
		{
			fieldname: "value",
			label: __("Value"),
			fieldtype: "Select",
			options:["Qty", "Amount"],
			default: "Qty",
			reqd: 0
		},
		
	]
};
