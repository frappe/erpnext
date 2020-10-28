// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Returned Materials Against Work Order"] = {
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
			fieldname:"to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1
		},
		{
			label: __("Work Order"),
			fieldname: "work_order",
			fieldtype: "Link",
			options: "Work Order"
		}
	]
};
