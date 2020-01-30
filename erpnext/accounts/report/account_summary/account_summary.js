// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Account Summary"] = {
	"filters": [
		{
			"fieldname":"report_from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"reqd": 1
		},
		{
			"fieldname":"report_to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"reqd": 1
		}
	]
};
