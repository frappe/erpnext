// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Balance Sheet"] = $.extend({}, erpnext.financial_statements);

erpnext.utils.add_dimensions("Balance Sheet", 10);

frappe.query_reports["Balance Sheet"]["filters"].push({
	fieldname: "selected_view",
	label: __("Select View"),
	fieldtype: "Select",
	options: [
		{ value: "Report", label: __("Report View") },
		{ value: "Growth", label: __("Growth View") },
	],
	default: "Report",
	reqd: 1,
});

frappe.query_reports["Balance Sheet"]["filters"].push({
	fieldname: "report_view",
	label: __("Report View"),
	fieldtype: "Select",
	options: ["Horizontal", "Vertical"],
	default: ["Vertical"],
	reqd: 1,
	depends_on: "eval:doc.selected_view == 'Report'",
	on_change: function () {
		frappe.query_report.export_dialog = undefined;
		frappe.query_report.refresh();
	},
});

frappe.query_reports["Balance Sheet"]["filters"].push({
	fieldname: "accumulated_values",
	label: __("Accumulated Values"),
	fieldtype: "Check",
	default: 1,
});

frappe.query_reports["Balance Sheet"]["filters"].push({
	fieldname: "include_default_book_entries",
	label: __("Include Default FB Entries"),
	fieldtype: "Check",
	default: 1,
});

frappe.query_reports["Balance Sheet"]["export_hidden_cols"] = true;
