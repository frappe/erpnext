// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Purchase Details"] = {
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
			fieldname: "doctype",
			label: __("Based On"),
			fieldtype: "Select",
			options: ["Purchase Order","Purchase Receipt","Purchase Invoice"],
			default: "Purchase Invoice",
			reqd: 1
		},
		{
			fieldname: "qty_field",
			label: __("Quantity Type"),
			fieldtype: "Select",
			options: ["Stock Qty", "Contents Qty", "Transaction Qty"],
			default: "Stock Qty",
			reqd: 1
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1
		},
		{
			fieldname: "supplier",
			label: __("Supplier"),
			fieldtype: "Link",
			options: "Supplier"
		},
		{
			fieldname: "supplier_group",
			label: __("Supplier Group"),
			fieldtype: "Link",
			options: "Supplier Group"
		},
		{
			fieldname: "item_code",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item"
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
			"fieldname":"cost_center",
			"label": __("Cost Center"),
			"fieldtype": "MultiSelectList",
			get_data: function(txt) {
				return frappe.db.get_link_options('Cost Center', txt, {
					company: frappe.query_report.get_filter_value("company")
				});
			}
		},
		{
			"fieldname":"project",
			"label": __("Project"),
			"fieldtype": "MultiSelectList",
			get_data: function(txt) {
				return frappe.db.get_link_options('Project', txt, {
					company: frappe.query_report.get_filter_value("company")
				});
			}
		},
		{
			fieldname: "group_by_1",
			label: __("Group By Level 1"),
			fieldtype: "Select",
			options: ["Ungrouped", "Group by Supplier", "Group by Supplier Group", "Group by Transaction",
				"Group by Item", "Group by Item Group", "Group by Brand"],
			default: "Ungrouped"
		},
		{
			fieldname: "group_by_2",
			label: __("Group By Level 2"),
			fieldtype: "Select",
			options: ["Ungrouped", "Group by Supplier", "Group by Supplier Group", "Group by Transaction",
				"Group by Item", "Group by Item Group", "Group by Brand"],
			default: "Group by Supplier"
		},
		{
			fieldname: "group_by_3",
			label: __("Group By Level 3"),
			fieldtype: "Select",
			options: ["Ungrouped", "Group by Supplier", "Group by Supplier Group", "Group by Transaction",
				"Group by Item", "Group by Item Group", "Group by Brand"],
			default: "Group by Transaction"
		},
		{
			fieldname: "group_same_items",
			label: __("Group Same Items"),
			fieldtype: "Check",
			default: 1
		},
		{
			fieldname: "show_basic_values",
			label: __("Show Basic Values"),
			fieldtype: "Check"
		},
		{
			fieldname: "show_tax_exclusive_values",
			label: __("Show Tax Exclusive Values"),
			fieldtype: "Check"
		},
		{
			fieldname: "show_discount_values",
			label: __("Show Discount Values"),
			fieldtype: "Check"
		},
		{
			fieldname: "include_taxes",
			label: __("Show Detailed Taxes"),
			fieldtype: "Check"
		},
	],
	"initial_depth": 1
}
