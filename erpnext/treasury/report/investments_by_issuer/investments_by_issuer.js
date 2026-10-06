// Copyright (c) 2026, Aagnya Mistry and contributors
// For license information, please see license.txt

frappe.query_reports["Investments by Issuer"] = {
	filters: [
		erpnext.treasury.get_company_filter(),
		erpnext.treasury.get_as_on_date_filter(),
		erpnext.treasury.get_investment_filters()[0],
	],
	formatter: erpnext.treasury.report_formatter,
};
