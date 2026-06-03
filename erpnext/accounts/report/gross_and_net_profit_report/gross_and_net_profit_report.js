// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

const GNP_REPORT = "Gross and Net Profit Report";

frappe.query_reports[GNP_REPORT] = $.extend({}, erpnext.financial_statements);

erpnext.utils.add_dimensions(GNP_REPORT, 10);

frappe.query_reports[GNP_REPORT]["filters"].push({
	fieldname: "accumulated_values",
	label: __("Accumulated Values"),
	fieldtype: "Check",
});
