// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Subcontract Order Summary"] = {
	"filters": [
		{
			label: __("Company"),
			fieldname: "company",
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1
		},
		{
			label: __("From Date"),
			fieldname:"from_date",
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1
		},
		{
			label: __("To Date"),
			fieldname:"to_date",
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1
		},
		{
			label: __("Purchase Order"),
			fieldname: "name",
			fieldtype: "Link",
			options: "Purchase Order",
			get_query: function() {
				return {
					filters: {
						docstatus: 1,
						is_subcontracted: 1,
						company: frappe.query_report.get_filter_value('company')
					}
				}
			}
		}
	]
};
