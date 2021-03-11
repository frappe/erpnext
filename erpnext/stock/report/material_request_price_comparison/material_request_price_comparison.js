// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Material Request Price Comparison"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label": __("From"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(),-1),
			"reqd": 1
		},
		{
			"fieldname":"to_date",
			"label": __("To"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname":"Category_purchase",
			"label": __("Category for purchase"),
			"fieldtype": "Link",
			"options": "Category for purchase",
			"reqd": 1
		},
	]
};
