// Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

<<<<<<< HEAD
const CF_REPORT_NAME = "Cash Flow";

frappe.query_reports[CF_REPORT_NAME] = $.extend(erpnext.financial_statements, {
=======
frappe.query_reports["Cash Flow"] = $.extend(erpnext.financial_statements, {
>>>>>>> 7c4cf3e834 (Favicon.svg)
	name_field: "section",
	parent_field: "parent_section",
});

<<<<<<< HEAD
erpnext.utils.add_dimensions(CF_REPORT_NAME, 10);
=======
erpnext.utils.add_dimensions("Cash Flow", 10);
>>>>>>> 7c4cf3e834 (Favicon.svg)

// The last item in the array is the definition for Presentation Currency
// filter. It won't be used in cash flow for now so we pop it. Please take
// of this if you are working here.

<<<<<<< HEAD
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
=======
frappe.query_reports["Cash Flow"]["filters"].splice(8, 1);

frappe.query_reports["Cash Flow"]["filters"].push({
	fieldname: "include_default_book_entries",
	label: __("Include Default FB Entries"),
	fieldtype: "Check",
	default: 1,
});
>>>>>>> 7c4cf3e834 (Favicon.svg)
