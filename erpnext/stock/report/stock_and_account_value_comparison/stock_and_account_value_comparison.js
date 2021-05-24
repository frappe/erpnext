// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Stock and Account Value Comparison"] = {
	"filters": [
		{
			"label": __("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"label": __("Account"),
			"fieldname": "account",
			"fieldtype": "Link",
			"options": "Account",
			get_query: function() {
				var company = frappe.query_report.get_filter_value('company');
				return {
					filters: {
						"account_type": "Stock",
						"company": company
					}
				}
			}
		},
		{
			"label": __("From Date"),
			"fieldname": "from_date",
			"fieldtype": "Date",
		},
		{
			"label": __("To Date"),
			"fieldname": "to_date",
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
		},
	]
};
