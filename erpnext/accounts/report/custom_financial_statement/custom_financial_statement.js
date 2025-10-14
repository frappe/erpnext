// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

const CFS_REPORT_NAME = "Custom Financial Statement";

frappe.query_reports[CFS_REPORT_NAME] = $.extend({}, erpnext.financial_statements);

erpnext.utils.add_dimensions(CFS_REPORT_NAME, 10);

frappe.query_reports[CFS_REPORT_NAME]["filters"].push(
	{
		fieldname: "report_template",
		label: __("Report Template"),
		fieldtype: "Link",
		options: "Financial Report Template",
		get_query: { filters: { disabled: 0 } },
		reqd: 1,
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
	}
);

frappe.query_reports[CFS_REPORT_NAME]["export_hidden_cols"] = true;
