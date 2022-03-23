// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Invoice Item Analysis"] = {
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
			default: frappe.defaults.get_user_default("year_start_date"),
			reqd: 1
		},
		{
			fieldname:"to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.defaults.get_user_default("year_end_date"),
			reqd: 1
		},
		{
			fieldname:"warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
			get_query: function() {
				const company = frappe.query_report.get_filter_value('company');
				return {
					filters: { 'company': company }
				}
			}
		},
		{
			fieldname:"territory",
			label: __("Territory"),
			fieldtype: "Link",
			options: "Territory"
		},
		{
			fieldname:"item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group"
		},
		{
			fieldname:"item_category",
			label: __("Item Category"),
			fieldtype: "Data"
			
		},
		{
			fieldname:"costcenter",
			label: __("Cost Center"),
			fieldtype: "Link",
			options: "Cost Center",
			get_query: function() {
				const company = frappe.query_report.get_filter_value('company');
				return {
					filters: { 'company': company }
				}
			}
		},
		{
			fieldname:"customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer"
		},
		{
			fieldname:"customer_group",
			label: __("Customer Group"),
			fieldtype: "Link",
			options: "Customer Group"
		},
		{
			fieldname:" sales_person",
			label: __("Sales Person"),
			fieldtype: "Link",
			options: "Sales Person"
		},
		{
			fieldname:"group_by",
			label: __("Group By"),
			fieldtype: "Select",
			default: "Customer Group",
			options: ["Months","Customer Group"],	
		},

	]
};
