// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Opportunity Summary by Sales Stage"] = {
	filters: [
		{
			fieldname: "based_on",
			label: __("Based On"),
			fieldtype: "Select",
			options: "Opportunity Owner\nSource\nOpportunity Type",
			default: "Opportunity Owner",
		},
		{
			fieldname: "data_based_on",
			label: __("Data Based On"),
			fieldtype: "Select",
			options: "Number\nAmount",
			default: "Number",
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
			fieldname: "status",
			label: __("Status"),
			fieldtype: "MultiSelectList",
			get_data: function () {
				return [
					{ value: "Open", description: "Status" },
					{ value: "Converted", description: "Status" },
					{ value: "Quotation", description: "Status" },
					{ value: "Replied", description: "Status" },
				];
			},
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
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
	],
};
