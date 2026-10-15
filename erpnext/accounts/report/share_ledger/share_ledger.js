// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Share Ledger"] = {
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
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "include_reversals",
			label: __("Include Reversals"),
			fieldtype: "Check",
			default: 1,
		},
	],
};
