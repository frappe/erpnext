// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Vehicle Sales Opportunities"] = {
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
			fieldname: "sales_person",
			label: __("Sales Person"),
			fieldtype: "Link",
			options: "Sales Person"
		},
		{
			fieldname: "lead_source",
			label: __("Source of Lead"),
			fieldtype: "Link",
			options: "Lead Source"
		},
		{
			fieldname: "information_source",
			label: __("Source of Information"),
			fieldtype: "Link",
			options: "Lead Information Source"
		},
		{
			fieldname: "variant_of",
			label: __("Model Interested In"),
			fieldtype: "Link",
			options: "Item",
			get_query: function() {
				return {
					query: "erpnext.controllers.queries.item_query",
					filters: {"is_vehicle": 1, "has_variants": 1, "include_disabled": 1}
				};
			}
		},
		{
			fieldname: "variant_item_code",
			label: __("Variant Interested In"),
			fieldtype: "Link",
			options: "Item",
			get_query: function() {
				var variant_of = frappe.query_report.get_filter_value('variant_of');
				var filters = {"is_vehicle": 1, "include_disabled": 1};
				if (variant_of) {
					filters['variant_of'] = variant_of;
				}
				return {
					query: "erpnext.controllers.queries.item_query",
					filters: filters
				};
			}
		},
		{
			fieldname: "lead_classification",
			label: __("Hot/Warm/Cold"),
			fieldtype: "Select",
			options: "\nHot\nWarm\nCold"
		},
		{
			fieldname: "sales_done",
			label: __("Sales Done"),
			fieldtype: "Select",
			options: "\nYes\nNo"
		},
	],
};
