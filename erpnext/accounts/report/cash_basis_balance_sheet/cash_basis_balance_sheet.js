// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

const CB_BS_REPORT_NAME = "Cash Basis Balance Sheet";

frappe.query_reports[CB_BS_REPORT_NAME] = $.extend({}, erpnext.financial_statements);

erpnext.utils.add_dimensions(CB_BS_REPORT_NAME, 10);

frappe.query_reports[CB_BS_REPORT_NAME]["filters"].push(
	{
		fieldname: "selected_view",
		label: __("Select View"),
		fieldtype: "Select",
		options: [
			{ value: "Report", label: __("Report View") },
			{ value: "Growth", label: __("Growth View") },
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
	}
);

frappe.query_reports[CB_BS_REPORT_NAME]["export_hidden_cols"] = true;
