// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Asset Balance"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname":"till_date",
			"label": __("Till Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname":"asset",
			"label": __("Asset"),
			"fieldtype": "Link",
			"options": "Asset"
		}
	]
};
