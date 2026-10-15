// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Equity Position"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
		},
		{
			fieldname: "shareholder",
			label: __("Shareholder"),
			fieldtype: "Link",
			options: "Shareholder",
		},
		{
			fieldname: "share_class",
			label: __("Share Class"),
			fieldtype: "Link",
			options: "Share Class",
		},
		{
			fieldname: "as_of_date",
			label: __("As of Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "include_zero_positions",
			label: __("Include Zero Positions"),
			fieldtype: "Check",
			default: 0,
		},
	],
};
