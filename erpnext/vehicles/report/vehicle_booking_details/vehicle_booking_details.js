// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Vehicle Booking Details"] = {
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
			fieldname: "date_type",
			label: __("Which Date"),
			fieldtype: "Select",
			options: ["Booking Date", "Vehicle Delivered Date", "Delivery Period"],
			default: "Booking Date",
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.defaults.get_user_default("year_start_date"),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.defaults.get_user_default("year_end_date"),
			reqd: 1,
		},
		{
			fieldname: "variant_of",
			label: __("Model Item Code"),
			fieldtype: "Link",
			options: "Item",
			get_query: function() {
				return {
					query: "erpnext.controllers.queries.item_query",
					filters: {"is_vehicle": 1, "include_in_vehicle_booking": 1, "include_disabled": 1, "has_variants": 1}
				};
			}
		},
		{
			fieldname: "item_code",
			label: __("Variant Item Code"),
			fieldtype: "Link",
			options: "Item",
			get_query: function() {
				var variant_of = frappe.query_report.get_filter_value('variant_of');
				var filters = {"is_vehicle": 1, "include_in_vehicle_booking": 1, "include_disabled": 1};
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
			fieldname: "customer",
			label: __("Customer (User)"),
			fieldtype: "Link",
			options: "Customer"
		},
		{
			fieldname: "financer",
			label: __("Financer"),
			fieldtype: "Link",
			options: "Customer"
		},
		{
			fieldname: "supplier",
			label: __("Supplier"),
			fieldtype: "Link",
			options: "Supplier"
		},
		{
			fieldname: "group_by_1",
			label: __("Group By Level 1"),
			fieldtype: "Select",
			options: ["Ungrouped", "Group by Variant", "Group by Model", "Group by Item Group", "Group by Brand",
				"Group by Delivery Period", "Group by Status"],
			default: "Ungrouped"
		},
		{
			fieldname: "group_by_2",
			label: __("Group By Level 2"),
			fieldtype: "Select",
			options: ["Ungrouped", "Group by Variant", "Group by Model", "Group by Item Group", "Group by Brand",
				"Group by Delivery Period", "Group by Status"],
			default: "Group by Model"
		},
		{
			fieldname: "group_by_3",
			label: __("Group By Level 3"),
			fieldtype: "Select",
			options: ["Ungrouped", "Group by Variant", "Group by Model", "Group by Item Group", "Group by Brand",
				"Group by Delivery Period", "Group by Status"],
			default: "Group by Variant"
		},
		{
			fieldname: "priority",
			label: __("High Priority Only"),
			fieldtype: "Check",
		},
	],
	formatter: function(value, row, column, data, default_formatter) {
		var style = {};

		if (data.original_item_code !== data.item_code && data.item_code !== data.variant_of) {
			if (['item_code', 'item_name', 'previous_item_code'].includes(column.fieldname)) {
				style['font-weight'] = 'bold';
				style['background-color'] = '#ffe2a7';
			}
		}

		if (data.previous_color && data.previous_color !== data.vehicle_color) {
			if (['vehicle_color', 'previous_color'].includes(column.fieldname)) {
				style['font-weight'] = 'bold';
				style['background-color'] = '#ffe2a7';
			}
		}

		if (data.priority) {
			if (['priority', 'delivery_period'].includes(column.fieldname)) {
				style['background-color'] = '#ffb7b7';
			}
		}

		return default_formatter(value, row, column, data, {css: style});
	},
	"initial_depth": 2
};
