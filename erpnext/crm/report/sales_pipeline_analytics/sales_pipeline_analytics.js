// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Sales Pipeline Analytics"] = {
	filters: [
		{
			fieldname: "pipeline_by",
			label: __("Pipeline By"),
			fieldtype: "Select",
			options: "Owner\nSales Stage",
			default: "Owner",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "range",
			label: __("Range"),
			fieldtype: "Select",
			options: "Monthly\nQuarterly",
			default: "Monthly",
		},
		{
			fieldname: "assigned_to",
			label: __("Assigned To"),
			fieldtype: "Link",
			options: "User",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "Open\nQuotation\nConverted\nReplied",
		},
		{
			fieldname: "based_on",
			label: __("Based On"),
			fieldtype: "Select",
			options: "Number\nAmount",
			default: "Number",
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "opportunity_source",
			label: __("Opportunity Source"),
			fieldtype: "Link",
			options: "Lead Source",
		},
		{
			fieldname: "opportunity_type",
			label: __("Opportunity Type"),
			fieldtype: "Link",
			options: "Opportunity Type",
		},
	],
};
