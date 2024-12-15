// Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Cash Flow"] = $.extend(erpnext.financial_statements, {
	name_field: "section",
	parent_field: "parent_section",
});

erpnext.utils.add_dimensions("Cash Flow", 10);

// The last item in the array is the definition for Presentation Currency
// filter. It won't be used in cash flow for now so we pop it. Please take
// of this if you are working here.

frappe.query_reports["Cash Flow"]["filters"].splice(8, 1);

frappe.query_reports["Cash Flow"]["filters"].push({
	fieldname: "include_default_book_entries",
	label: __("Include Default FB Entries"),
	fieldtype: "Check",
	default: 1,
});
