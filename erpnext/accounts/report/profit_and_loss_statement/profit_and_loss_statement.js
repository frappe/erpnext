// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.require("assets/erpnext/js/financial_statements.js", function () {
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
	});

	frappe.query_reports["Profit and Loss Statement"]["filters"].push({
		fieldname: "include_default_book_entries",
		label: __("Include Default Book Entries"),
		fieldtype: "Check",
		default: 1,
	});
});
