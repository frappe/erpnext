// Copyright (c) 2026, Aagnya Mistry and contributors
// For license information, please see license.txt

frappe.query_reports["Upcoming Maturities"] = {
	filters: [
		erpnext.treasury.get_company_filter(),
		erpnext.treasury.get_as_on_date_filter(),
		...erpnext.treasury.get_investment_filters(),
	],
	formatter: erpnext.treasury.report_formatter,
};
