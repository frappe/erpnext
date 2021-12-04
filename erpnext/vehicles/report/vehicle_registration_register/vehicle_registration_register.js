// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

{% include 'erpnext/vehicles/doctype/vehicle_registration_order/vehicle_registration_order_list.js' %}

frappe.query_reports["Vehicle Registration Register"] = {
	filters: [
		{
			fieldname: "order_status",
			label: __("Order Status"),
			fieldtype: "Select",
			options: ["", "Open Orders", "Closed Orders"],
			default: "Open Orders",
		},
		{
			fieldname: "registration_status",
			label: __("Registration Status"),
			fieldtype: "Select",
			options: ["", "Registered", "Unregistered"],
		},
		{
			fieldname: "invoice_status",
			label: __("Invoice Status"),
			fieldtype: "Select",
			options: ["", "Not Received", "In Hand", "Issued", "Delivered"],
		},
		{
			fieldname: "date_type",
			label: __("Which Date"),
			fieldtype: "Select",
			options: ["Order Date", "Registration Receipt Date", "Call Date",
				"Invoice Delivered Date", "Invoice Issue Date", "Invoice Return Date"],
			default: "Order Date",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1
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
			fieldname: "vehicle",
			label: __("Vehicle"),
			fieldtype: "Link",
			options: "Vehicle"
		},
		{
			fieldname: "vehicle_booking_order",
			label: __("Vehicle Booking Order"),
			fieldtype: "Link",
			options: "Vehicle Booking Order"
		},
		{
			fieldname: "registration_customer",
			label: __("Registration Customer"),
			fieldtype: "Link",
			options: "Customer",
			get_query: function() {
				return {
					query: "erpnext.controllers.queries.customer_query"
				};
			}
		},
		{
			fieldname: "customer",
			label: __("Payment Customer"),
			fieldtype: "Link",
			options: "Customer",
			get_query: function() {
				return {
					query: "erpnext.controllers.queries.customer_query"
				};
			}
		},
		{
			fieldname: "agent",
			label: __("Agent"),
			fieldtype: "Link",
			options: "Agent"
		},
		{
			fieldname: "group_by_1",
			label: __("Group By Level 1"),
			fieldtype: "Select",
			options: ["Ungrouped", "Group by Variant", "Group by Model", "Group by Item Group", "Group by Brand",
				"Group by Status"],
			default: "Ungrouped"
		},
		{
			fieldname: "group_by_2",
			label: __("Group By Level 2"),
			fieldtype: "Select",
			options: ["Ungrouped", "Group by Variant", "Group by Model", "Group by Item Group", "Group by Brand",
				"Group by Status"],
			default: "Ungrouped"
		},
		{
			fieldname: "group_by_3",
			label: __("Group By Level 3"),
			fieldtype: "Select",
			options: ["Ungrouped", "Group by Variant", "Group by Model", "Group by Item Group", "Group by Brand",
				"Group by Status"],
			default: "Ungrouped"
		},
	],
	formatter: function(value, row, column, data, default_formatter) {
		var style = {};

		if (data.status == "Cancelled Booking") {
			style['color'] = 'red';
		}

		$.each(['customer_outstanding', 'authority_outstanding', 'agent_outstanding'], function (i, f) {
			if (column.fieldname === f) {
				var outstanding = flt(data[f]);
				if (outstanding > 0) {
					style['color'] = 'orange';
				} else if (outstanding < 0) {
					style['color'] = 'red';
				} else {
					style['color'] = 'green';
				}
			}
		});

		if (column.fieldname == 'status') {
			if (frappe.listview_settings['Vehicle Registration Order']) {
				var indicator = frappe.listview_settings['Vehicle Registration Order'].get_indicator(data);
				if (indicator) {
					var indicator_color = indicator[1];
					return `<span class="indicator ${indicator_color}"><span>${data.status}</span></span>`;
				}
			}
		}

		return default_formatter(value, row, column, data, {css: style});
	},
	"initial_depth": 1
};
