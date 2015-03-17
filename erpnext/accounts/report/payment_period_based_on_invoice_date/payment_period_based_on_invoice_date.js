// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Payment Period Based On Invoice Date"] = {
	"filters": [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.defaults.get_user_default("year_start_date"),
		},
		{
			fieldname:"to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: get_today()
		},
		{
			fieldname:"payment_type",
			label: __("Payment Type"),
			fieldtype: "Select",
			options: "Incoming\nOutgoing",
			default: "Incoming"
		},
		{
			fieldname:"account",
			label: __("Account"),
			fieldtype: "Link",
			options: "Account",
			get_query: function() {
				return {
					query: "erpnext.controllers.queries.get_account_list", 
					filters: {
						"report_type": "Balance Sheet",
						company: frappe.query_report.filters_by_name.company.get_value()
					}
				}
			}
		},
		{
			fieldname:"company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("company")
		},
	]
}