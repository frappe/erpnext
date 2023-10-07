// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


frappe.query_reports["Profit and Loss Statement"] = $.extend(
	{},
	erpnext.financial_statements
);

erpnext.utils.add_dimensions("Profit and Loss Statement", 10);

frappe.query_reports["Profit and Loss Statement"]["filters"].push({
	fieldname: "accumulated_values",
	label: __("Accumulated Values"),
	fieldtype: "Check",
	default: 1,
});
