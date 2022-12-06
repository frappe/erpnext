// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Warehouse Wise Stock Balance"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"reqd": 1,
			"default": frappe.defaults.get_user_default("Company")
		}
	],
	"initial_depth": 3,
	"tree": true,
	"parent_field": "parent_warehouse",
	"name_field": "warehouse"
};
