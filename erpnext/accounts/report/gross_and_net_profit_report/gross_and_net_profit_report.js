// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

const GNP_REPORT = "Gross and Net Profit Report";

frappe.query_reports[GNP_REPORT] = $.extend({}, erpnext.financial_statements, {
	// own list: the shared one may already hold the filters pushed by another financial report
	// whose script was loaded earlier in the session (e.g. by a dashboard chart)
	filters: erpnext.financial_statements.get_filters(),
});

erpnext.utils.add_dimensions(GNP_REPORT, 10);

frappe.query_reports[GNP_REPORT]["filters"].push({
	fieldname: "accumulated_values",
	label: __("Accumulated Values"),
	fieldtype: "Check",
});
