// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Stock Ageing"] = {
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
			fieldname: "to_date",
			label: __("As On Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1
		},
		{
			fieldname: "item_code",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
			get_query: function() {
				return {
					query: "erpnext.controllers.queries.item_query",
					filters: {"include_disabled": 1, "include_templates": 1}
				};
			},
			on_change: function() {
				var item_code = frappe.query_report.get_filter_value('item_code');
				if (!item_code) {
					frappe.query_report.set_filter_value('item_name', "");
				} else {
					frappe.db.get_value("Item", item_code, 'item_name', function(value) {
						frappe.query_report.set_filter_value('item_name', value['item_name']);
					});
				}
			}
		},
		{
			fieldname: "item_name",
			label: __("Item Name"),
			fieldtype: "Data",
			hidden: 1
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse"
		},
		{
			fieldname: "batch_no",
			label: __("Batch No"),
			fieldtype: "Link",
			options: "Batch"
		},
		{
			fieldname: "packing_slip",
			label: __("Package"),
			fieldtype: "Link",
			options: "Packing Slip"
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
		{
			fieldname: "package_wise_stock",
			label: __("Package Wise Stock"),
			fieldtype: "Select",
			options: ["", "Packed and Unpacked Stock", "Packed Stock", "Unpacked Stock"],
		},
		{
			fieldname: "consolidate_warehouse",
			label: __("Consolidate Warehouse"),
			fieldtype: "Check",
		},
		{
			fieldname: "batch_wise_stock",
			label: __("Batch Wise Stock"),
			fieldtype: "Check",
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		var style = {};

		if (["average_age"].includes(column.fieldname)) {
			style['font-weight'] = 'bold';
		}

		return default_formatter(value, row, column, data, {css: style});
	},
}
