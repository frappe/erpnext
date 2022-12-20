// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Consolidation Report"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label":__("From Date"),
			"fieldtype":"Date",
			"reqd":1,
			"default":frappe.datetime.year_start()
		},
		{
			"fieldname":"to_date",
			"label":__("To Date"),
			"fieldtype":"Date",
			"reqd":1,
			"default":frappe.datetime.month_end()
		},
		{
			"fieldname":"is_inter_company",
			"label":__("Is Inter Company"),
			"fieldtype":"Select",
			"options":['','Yes','No']
		},
	]
};
