// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
// For license information, please see license.txt

frappe.query_reports["Stock Balance"] = {
	"filters": [
		{
			"fieldname":"qty_field",
			"label": __("Stock Qty or Contents Qty"),
			"fieldtype": "Select",
			"options": "Stock Qty\nContents Qty",
			"default": "Stock Qty"
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"width": "80",
			"reqd": 1,
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"width": "80",
			"reqd": 1,
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname": "item_code",
			"label": __("Item"),
			"fieldtype": "Link",
			"width": "80",
			"options": "Item",
			"get_query": function() {
				return {
					query: "erpnext.controllers.queries.item_query",
				};
			}
		},
		{
			"fieldname": "warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"width": "80",
			"options": "Warehouse",
			get_query: () => {
				var warehouse_type = frappe.query_report.get_filter_value('warehouse_type');
				if(warehouse_type){
					return {
						filters: {
							'warehouse_type': warehouse_type
						}
					};
				}
			}
		},
		{
			"fieldname": "warehouse_type",
			"label": __("Warehouse Type"),
			"fieldtype": "Link",
			"width": "80",
			"options": "Warehouse Type"
		},
		{
			"fieldname": "item_group",
			"label": __("Item Group"),
			"fieldtype": "Link",
			"width": "80",
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
			"fieldname": "filter_item_without_transactions",
			"label": __("Filter Items Without Transactons"),
			"fieldtype": "Check",
			"default": 1
		},
		{
			"fieldname": "consolidated",
			"label": __("Consolidated Values"),
			"fieldtype": "Check"
		},
		{
			"fieldname": "show_projected_qty",
			"label": __("Show Projected Qty"),
			"fieldtype": "Check"
		},
		{
			"fieldname": "show_variant_attributes",
			"label": __("Show Variant Attributes"),
			"fieldtype": "Check"
		},
		{
			"fieldname": 'show_stock_ageing_data',
			"label": __('Show Stock Ageing Data'),
			"fieldtype": 'Check'
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		var style = {};

		if (["out_qty", "out_val"].includes(column.fieldname) && flt(value) > 0) {
			style['color'] = 'red';
		} else if (["in_qty", "in_val", "ordered_qty"].includes(column.fieldname) && flt(value) > 0) {
			style['color'] = 'green';
		}

		if (column.fieldname == "bal_qty") {
			style['font-weight'] = 'bold';
		}
		if (["bal_qty", "bal_val"].includes(column.fieldname)) {
			if (flt(value) > 0) {
				style['color'] = '#004509';
			} else if (value === 0) {
				style['color'] = '#00009a';
			}
		}

		if (["bal_qty", "bal_val", "opening_qty", "opening_val"].includes(column.fieldname) && flt(value) < 0) {
			style['background-color'] = 'pink';
		}

		return default_formatter(value, row, column, data, {css: style});
	}
};
