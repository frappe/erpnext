// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["YoY Item Wise Dealer Sales"] = {
	"filters": [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options:"Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options:"Customer",
			reqd: 1,
			on_change: () => {
				var cust = frappe.query_report.get_filter_value('customer');
				if (cust) {
					frappe.db.get_value('Customer', cust, "customer_name", function(value) {
						frappe.query_report.set_filter_value('customer_name', value["customer_name"]);
					});
				} else {
					frappe.query_report.set_filter_value('customer_name', "");
				}
			}
		},
		{
			fieldname: "customer_name",
			label: __("Customer Name"),
			fieldtype: "Data",
			fetch_from: "customer.fullname",
			read_only: 1
		},
		{
			fieldname: "month",
			label: __("Mont"),
			fieldtype: "Data",
			default: "April to March",
			read_only: 1
		},
		{
			fieldname: "from_year",
			label: __("From Year"),
			fieldtype: "Int",
			default: 2020,
			reqd: 1
		},
		{
			fieldname: "to_year",
			label: __("To Year"),
			fieldtype: "Int",
			default: 2022,
			reqd: 1
		},
		{
			fieldname: "value",
			label: __("Value"),
			fieldtype: "Select",
			options:["Qty", "Amount"],
			default: "Qty",
			reqd: 0
		},
		
	]
};

