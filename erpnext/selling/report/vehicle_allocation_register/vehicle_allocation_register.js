// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Vehicle Allocation Register"] = {
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
			fieldname: "from_allocation_period",
			label: __("From Allocation Period"),
			fieldtype: "Link",
			options: "Vehicle Allocation Period"
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
			options: "Vehicle Allocation Period"
		},
		{
			fieldname: "to_delivery_period",
			label: __("To Delivery Period"),
			fieldtype: "Link",
			options: "Vehicle Allocation Period"
		},
		{
			fieldname: "item_code",
			label: __("Vehicle Item Code (Variant)"),
			fieldtype: "Link",
			options: "Item",
			get_query: function() {
				return {
					query: "erpnext.controllers.queries.item_query",
					filters: {"is_vehicle": 1, "include_in_vehicle_booking": 1}
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
			options: ["Ungrouped", "Group by Allocation Period", "Group by Delivery Period",
				"Group by Item", "Group by Item Group", "Group by Brand",
				"Group by Customer", "Group by Customer Group", "Group by Territory", "Group by Sales Person"],
			default: "Ungrouped"
		},
		{
			fieldname: "group_by_2",
			label: __("Group By Level 2"),
			fieldtype: "Select",
			options: ["Ungrouped", "Group by Allocation Period", "Group by Delivery Period",
				"Group by Item", "Group by Item Group", "Group by Brand",
				"Group by Customer", "Group by Customer Group", "Group by Territory", "Group by Sales Person"],
			default: "Group by Allocation Period"
		},
		{
			fieldname: "group_by_3",
			label: __("Group By Level 3"),
			fieldtype: "Select",
			options: ["Ungrouped", "Group by Allocation Period", "Group by Delivery Period",
				"Group by Item", "Group by Item Group", "Group by Brand",
				"Group by Customer", "Group by Customer Group", "Group by Territory", "Group by Sales Person"],
			default: "Group by Item"
		},
	],
	"initial_depth": 1
};
