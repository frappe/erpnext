// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Investment Returns"] = {
	filters: [
		erpnext.treasury.get_company_filter(),
		...erpnext.treasury.get_period_filters(),
		...erpnext.treasury.get_investment_filters(),
	],
	formatter: erpnext.treasury.report_formatter,
};
