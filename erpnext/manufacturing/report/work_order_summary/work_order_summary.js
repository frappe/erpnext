// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Work Order Summary"] = {
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
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -12),
			reqd: 1
		},
		{
			label: __("To Date"),
			fieldname:"to_date",
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			label: __("Status"),
			fieldname: "status",
			fieldtype: "Select",
			options: ["", "Not Started", "In Process", "Completed", "Stopped"]
		},
		{
			label: __("Sales Orders"),
			fieldname: "sales_order",
			fieldtype: "MultiSelectList",
			get_data: function(txt) {
				return frappe.db.get_link_options('Sales Order', txt);
			}
		},
		{
			label: __("Production Item"),
			fieldname: "production_item",
			fieldtype: "MultiSelectList",
			get_data: function(txt) {
				return frappe.db.get_link_options('Item', txt);
			}
		},
		{
			label: __("Age"),
			fieldname:"age",
			fieldtype: "Int",
			default: "0"
		},
		{
			label: __("Charts Based On"),
			fieldname:"charts_based_on",
			fieldtype: "Select",
			options: ["Status", "Age", "Quantity"],
			default: "Status"
		},
	]
};
