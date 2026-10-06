// Copyright (c) 2026, Aagnya Mistry and contributors
// For license information, please see license.txt

frappe.query_reports["Bank and Cash Balances"] = {
	filters: [
		erpnext.treasury.get_company_filter(),
		erpnext.treasury.get_as_on_date_filter(),
		{
			fieldname: "show_zero_balances",
			label: __("Show Zero Balances"),
			fieldtype: "Check",
		},
	],
	formatter: erpnext.treasury.report_formatter,
};
