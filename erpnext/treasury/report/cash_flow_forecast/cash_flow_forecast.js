// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Cash Flow Forecast"] = {
	filters: [
		erpnext.treasury.get_company_filter(),
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "periodicity",
			label: __("Periodicity"),
			fieldtype: "Select",
			options: ["Weekly", "Monthly"],
			default: "Monthly",
			reqd: 1,
		},
		{
			fieldname: "periods",
			label: __("Number of Periods"),
			fieldtype: "Int",
			default: 6,
			reqd: 1,
		},
		{
			fieldname: "include_overdue",
			label: __("Include Overdue in First Period"),
			fieldtype: "Check",
			default: 1,
		},
	],
	formatter: erpnext.treasury.report_formatter,
};
