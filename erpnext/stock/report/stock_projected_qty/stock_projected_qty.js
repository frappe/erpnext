// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Stock Projected Qty"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname":"qty_field",
			"label": __("Stock Qty or Contents Qty"),
			"fieldtype": "Select",
			"options": "Stock Qty\nContents Qty",
			"default": "Stock Qty"
		},
		{
			"fieldname":"warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse"
		},
		{
			"fieldname":"item_code",
			"label": __("Item"),
			"fieldtype": "Link",
			"options": "Item",
			"get_query": function() {
				return {
					query: "erpnext.controllers.queries.item_query"
				}
			}
		},
		{
			"fieldname":"item_group",
			"label": __("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group"
		},
		{
			"fieldname":"brand",
			"label": __("Brand"),
			"fieldtype": "Link",
			"options": "Brand"
		},
		{
			fieldname: "item_source",
			label: __("Item Source"),
			fieldtype: "Link",
			options: "Item Source"
		},
		{
			"fieldname":"include_uom",
			"label": __("Include UOM"),
			"fieldtype": "Link",
			"options": "UOM"
		},
		{
			fieldname: "group_by_1",
			label: __("Group By Level 1"),
			fieldtype: "Select",
			options: ["Ungrouped", "Group by Item", "Group by Warehouse", "Group by Item Group", "Group by Brand"],
			default: "Ungrouped"
		},
		{
			fieldname: "group_by_2",
			label: __("Group By Level 2"),
			fieldtype: "Select",
			options: ["Ungrouped", "Group by Item", "Group by Warehouse", "Group by Item Group", "Group by Brand"],
			default: "Group by Item"
		},
	],
	formatter: function(value, row, column, data, default_formatter) {
		var style = {};
		if (['actual_qty', 'projected_qty', 'shortage_qty'].includes(column.fieldname)) {
			if (flt(value) < 0) {
				style['background-color'] = 'pink';
				style['font-weight'] = 'bold';
			}
		}

		if (['projected_qty', 'ordered_qty', 'planned_qty', 'indented_qty'].includes(column.fieldname)) {
			if (flt(value) > 0) {
				style['color'] = 'green';
			} else if(flt(value) < 0 && column.fieldname !== 'projected_qty') {
				style['color'] = 'red';
			}
		}

		if (['reserved_qty', 'reserved_qty_for_production', 'reserved_qty_for_sub_contract'].includes(column.fieldname)) {
			if (flt(value) > 0) {
				style['color'] = 'red';
			} else if(flt(value) < 0) {
				style['color'] = 'green';
			}
		}

		return default_formatter(value, row, column, data, {css: style});
	},
	"initial_depth": 0
}
