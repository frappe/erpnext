// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Profit and Loss Statement"] = $.extend({}, erpnext.financial_statements);

erpnext.utils.add_dimensions("Profit and Loss Statement", 10);

frappe.query_reports["Profit and Loss Statement"]["filters"].push({
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
	on_change: function () {
		let filter_based_on = frappe.query_reports.get_filter_value("selected_view");
		frappe.query_reports.toggle_filter_display("report_view", filter_based_on === "Report");
		frappe.query_reports.refresh();
	},
});

frappe.query_reports["Profit and Loss Statement"]["filters"].push({
	fieldname: "report_view",
	label: __("Report View"),
	fieldtype: "Select",
	options: ["Horizontal", "Vertical"],
	default: ["Vertical"],
	reqd: 1,
	depends_on: "eval:doc.selected_view == 'Report'",
});
frappe.query_reports["Profit and Loss Statement"]["filters"].push({
	fieldname: "accumulated_values",
	label: __("Accumulated Values"),
	fieldtype: "Check",
	default: 1,
});
