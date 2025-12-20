// Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

const CF_REPORT_NAME = "Cash Flow";

frappe.query_reports[CF_REPORT_NAME] = $.extend(erpnext.financial_statements, {
	name_field: "section",
	parent_field: "parent_section",
});

erpnext.utils.add_dimensions(CF_REPORT_NAME, 10);

// The last item in the array is the definition for Presentation Currency
// filter. It won't be used in cash flow for now so we pop it. Please take
// of this if you are working here.

frappe.query_reports[CF_REPORT_NAME]["filters"].splice(8, 1);

frappe.query_reports[CF_REPORT_NAME]["filters"].push(
	{
		fieldname: "report_template",
		label: __("Report Template"),
		fieldtype: "Link",
		options: "Financial Report Template",
		get_query: { filters: { report_type: CF_REPORT_NAME, disabled: 0 } },
	},
	{
		fieldname: "show_account_details",
		label: __("Account Detail Level"),
		fieldtype: "Select",
		options: ["Summary", "Account Breakdown"],
		default: "Summary",
		depends_on: "eval:doc.report_template",
	},
	{
		fieldname: "include_default_book_entries",
		label: __("Include Default FB Entries"),
		fieldtype: "Check",
		default: 1,
	},
	{
		fieldname: "show_opening_and_closing_balance",
		label: __("Show Opening and Closing Balance"),
		fieldtype: "Check",
	}
);
