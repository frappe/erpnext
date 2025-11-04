// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Issue Summary"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "based_on",
			label: __("Based On"),
			fieldtype: "Select",
			options: ["Customer", "Issue Type", "Issue Priority", "Assigned To"],
			default: "Customer",
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.defaults.get_global_default("year_start_date"),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.defaults.get_global_default("year_end_date"),
			reqd: 1,
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: [
				"",
				{ label: __("Open"), value: "Open" },
				{ label: __("Replied"), value: "Replied" },
				{ label: __("On Hold"), value: "On Hold" },
				{ label: __("Resolved"), value: "Resolved" },
				{ label: __("Closed"), value: "Closed" },
			],
		},
		{
			fieldname: "priority",
			label: __("Issue Priority"),
			fieldtype: "Link",
			options: "Issue Priority",
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "Project",
		},
		{
			fieldname: "assigned_to",
			label: __("Assigned To"),
			fieldtype: "Link",
			options: "User",
		},
	],
};
