// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Products Sold By Item Group"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname":"from_time",
			"label": __("From Time"),
			"fieldtype": "Time",
			"reqd": 1
		},
		{
			"fieldname":"to_time",
			"label": __("To Time"),
			"fieldtype": "Time",
			"reqd": 1
		},
		{
			"fieldname":"prefix",
			"label": __("Prefix"),
			"fieldtype": "Link",
			"options": "Prefix sales for days",
			"reqd": 1
		},
		{
			"fieldname":"user",
			"label": __("User"),
			"fieldtype": "Link",
			"options": "User"
		}
	]
};
