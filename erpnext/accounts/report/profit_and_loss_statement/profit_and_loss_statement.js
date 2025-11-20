// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

const PL_REPORT_NAME = "Profit and Loss Statement";

frappe.query_reports[PL_REPORT_NAME] = $.extend({}, erpnext.financial_statements);

erpnext.utils.add_dimensions(PL_REPORT_NAME, 10);

frappe.query_reports[PL_REPORT_NAME]["filters"].push(
	{
		fieldname: "report_template",
		label: __("Report Template"),
		fieldtype: "Link",
		options: "Financial Report Template",
		get_query: { filters: { report_type: PL_REPORT_NAME, disabled: 0 } },
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
		fieldname: "selected_view",
		label: __("Select View"),
		fieldtype: "Select",
		options: [
			{ value: "Report", label: __("Report View") },
			{ value: "Growth", label: __("Growth View") },
			{ value: "Margin", label: __("Margin View") },
		],
		default: "Report",
		reqd: 1,
	},
	{
		fieldname: "accumulated_values",
		label: __("Accumulated Values"),
		fieldtype: "Check",
		default: 1,
	},
	{
		fieldname: "include_default_book_entries",
		label: __("Include Default FB Entries"),
		fieldtype: "Check",
		default: 1,
	},
	{
		fieldname: "show_zero_values",
		label: __("Show zero values"),
		fieldtype: "Check",
		depends_on: "eval:!doc.report_template",
	}
);

frappe.query_reports[PL_REPORT_NAME]["export_hidden_cols"] = true;
