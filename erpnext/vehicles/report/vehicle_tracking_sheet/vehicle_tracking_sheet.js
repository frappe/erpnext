// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Vehicle Tracking Sheet"] = {
	"filters": [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today()
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today()
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
			fieldname: "project_type",
			label: __("Project Type"),
			fieldtype: "Link",
			options: "Project Type"
		},
		{
			fieldname: "customer",
			label: __("Customer (User)"),
			fieldtype: "Link",
			options: "Customer",
			get_query: function() {
				return {
					query: "erpnext.controllers.queries.customer_query"
				};
			}
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
			fieldname: "show_customer_in_print",
			label: __("Show Customer In Print"),
			fieldtype: "Check",
			default: 1,
			on_change: function() { return false; }
		},
	],
	formatter: function(value, row, column, data, default_formatter) {
		var style = {};

		if (['ready_to_close_dt_fmt', 'expected_delivery_dt_fmt'].includes(column.fieldname) && data.time_color) {
			style['color'] = data.time_color || 'orange';
		}

		if (column.fieldname == "vehicle_license_plate" && data.vehicle_unregistered) {
			style['font-weight'] = 'bold';
		}

		return default_formatter(value, row, column, data, {css: style});
	}
};
