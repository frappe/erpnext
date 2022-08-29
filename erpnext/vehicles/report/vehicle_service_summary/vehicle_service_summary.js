// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Vehicle Service Summary"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1
		},
		{
			fieldname:"from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1
		},
		{
			fieldname:"to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_end(),
			reqd: 1
		},
		{
			fieldname:"status",
			label: __("Status"),
			fieldtype: "Select",
			options: ["", "Open", "To Close", "Closed", "Closed or To Close", "Cancelled"]
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "Project",
		},
		{
			fieldname: "project_type",
			label: __("Project Type"),
			fieldtype: "Link",
			options: "Project Type",
		},
		{
			fieldname: "project_workshop",
			label: __("Project Workshop"),
			fieldtype: "Link",
			options: "Project Workshop"
		},
		{
			fieldname: "service_advisor",
			label: __("Service Advisor"),
			fieldtype: "Link",
			options: "Sales Person"
		},
		{
			fieldname: "service_manager",
			label: __("Service Manager"),
			fieldtype: "Link",
			options: "Sales Person"
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
			get_query: function() {
				return {
					query: "erpnext.controllers.queries.customer_query"
				};
			}
		},
		{
			fieldname: "customer_group",
			label: __("Customer Group"),
			fieldtype: "Link",
			options: "Customer Group"
		},
		{
			fieldname: "territory",
			label: __("Territory"),
			fieldtype: "Link",
			options: "Territory"
		},
		{
			fieldname: "applies_to_vehicle",
			label: __("Vehicle"),
			fieldtype: "Link",
			options: "Vehicle"
		},
		{
			fieldname: "applies_to_variant_of",
			label: __("Model Item Code"),
			fieldtype: "Link",
			options: "Item",
			get_query: function() {
				return {
					query: "erpnext.controllers.queries.item_query",
					filters: {"is_vehicle": 1, "has_variants": 1, "include_disabled": 1}
				};
			},
			on_change: function() {
				var variant_of = frappe.query_report.get_filter_value('applies_to_variant_of');
				if(!variant_of) {
					frappe.query_report.set_filter_value('applies_to_variant_of_name', "");
				} else {
					frappe.db.get_value("Item", variant_of, 'item_name', function(value) {
						frappe.query_report.set_filter_value('applies_to_variant_of_name', value['item_name']);
					});
				}
			}
		},
		{
			fieldname: "applies_to_variant_of_name",
			label: __("Model Name"),
			fieldtype: "Data",
			hidden: 1
		},
		{
			fieldname: "applies_to_item",
			label: __("Variant Item Code"),
			fieldtype: "Link",
			options: "Item",
			get_query: function() {
				var variant_of = frappe.query_report.get_filter_value('applies_to_variant_of');
				var filters = {"is_vehicle": 1, "include_disabled": 1};
				if (variant_of) {
					filters['variant_of'] = variant_of;
				}
				return {
					query: "erpnext.controllers.queries.item_query",
					filters: filters
				};
			},
			on_change: function() {
				var item_code = frappe.query_report.get_filter_value('applies_to_item');
				if(!item_code) {
					frappe.query_report.set_filter_value('applies_to_item_name', "");
				} else {
					frappe.db.get_value("Item", item_code, 'item_name', function(value) {
						frappe.query_report.set_filter_value('applies_to_item_name', value['item_name']);
					});
				}
			}
		},
		{
			fieldname: "applies_to_item_name",
			label: __("Variant Item Name"),
			fieldtype: "Data",
			hidden: 1
		},
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group"
		},
		{
			fieldname: "brand",
			label: __("Brand"),
			fieldtype: "Link",
			options: "Brand"
		},
		{
			fieldname: "item_source",
			label: __("Item Source"),
			fieldtype: "Link",
			options: "Item Source"
		},
	]
};
