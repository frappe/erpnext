// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Group Of Products Solds"] = {
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
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname":"prefix",
			"label": __("Serie"),
			"fieldtype": "Link",
			"options": "Daily summary series",
			"reqd": 1
		}
	]
};
