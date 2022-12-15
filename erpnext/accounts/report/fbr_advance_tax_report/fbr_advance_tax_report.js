// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["FBR Advance Tax Report"] = {
	"filters": [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_end(),
			reqd: 1
		},
		{
			fieldname: "account",
			label: __("Advance Tax Account"),
			fieldtype: "Link",
			options: "Account",
			get_query: function () {
				var company = frappe.query_report.get_filter_value('company');
				return {
					query: "erpnext.accounts.report.fbr_advance_tax_report.fbr_advance_tax_report.advance_tax_account_query",
					filters: {
						company: company
					}
				}
			},
		},
		{
			fieldname: "for_export",
			label: __("For Export"),
			fieldtype: "Check",
		},
	]
};
