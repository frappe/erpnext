// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Payment Period Based On Invoice Date"] = {
	"filters": [
		{
			fieldname: "from_date",
			label: frappe._("From Date"),
			fieldtype: "Date",
			default: frappe.defaults.get_user_default("year_start_date"),
		},
		{
			fieldname:"to_date",
			label: frappe._("To Date"),
			fieldtype: "Date",
			default: get_today()
		},
		{
			fieldname:"payment_type",
			label: frappe._("Payment Type"),
			fieldtype: "Select",
			options: "Incoming\nOutgoing",
			default: "Incoming"
		},
		{
			fieldname:"account",
			label: frappe._("Account"),
			fieldtype: "Link",
			options: "Account",
			get_query: function() {
				return {
					query: "accounts.utils.get_account_list", 
					filters: {
						is_pl_account: "No",
						company: frappe.query_report.filters_by_name.company.get_value()
					}
				}
			}
		},
		{
			fieldname:"company",
			label: frappe._("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_default("company")
		},
	]
}