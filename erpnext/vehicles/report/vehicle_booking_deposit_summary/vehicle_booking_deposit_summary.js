// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Vehicle Booking Deposit Summary"] = {
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
			fieldname: "deposit_type",
			label: __("Deposit Type"),
			fieldtype: "Select",
			options: "\nNCS\nDirect Deposit"
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
			fieldname: "from_allocation_period",
			label: __("From Allocation Period"),
			fieldtype: "Link",
			options: "Vehicle Allocation Period",
			on_change: function () {
				var period = frappe.query_report.get_filter_value('from_allocation_period');
				if (period) {
					frappe.query_report.set_filter_value('to_allocation_period', period);
				}
			}
		},
		{
			fieldname: "to_allocation_period",
			label: __("To Allocation Period"),
			fieldtype: "Link",
			options: "Vehicle Allocation Period"
		},
		{
			fieldname: "from_delivery_period",
			label: __("From Delivery Period"),
			fieldtype: "Link",
			options: "Vehicle Allocation Period",
			on_change: function () {
				var period = frappe.query_report.get_filter_value('from_delivery_period');
				if (period) {
					frappe.query_report.set_filter_value('to_delivery_period', period);
				}
			}
		},
		{
			fieldname: "to_delivery_period",
			label: __("To Delivery Period"),
			fieldtype: "Link",
			options: "Vehicle Allocation Period"
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
			options: ["Ungrouped", "Group by Allocation Period", "Group by Delivery Period",
				"Group by Variant", "Group by Model"],
			default: "Ungrouped"
		},
		{
			fieldname: "group_by_2",
			label: __("Group By Level 2"),
			fieldtype: "Select",
			options: ["Ungrouped", "Group by Allocation Period", "Group by Delivery Period",
				"Group by Variant", "Group by Model"],
			default: "Ungrouped"
		},
		{
			fieldname: "group_by_3",
			label: __("Group By Level 3"),
			fieldtype: "Select",
			options: ["Ungrouped", "Group by Allocation Period", "Group by Delivery Period",
				"Group by Variant", "Group by Model"],
			default: "Ungrouped"
		},
	],
	"initial_depth": 1
};
