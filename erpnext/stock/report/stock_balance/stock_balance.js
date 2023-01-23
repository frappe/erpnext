// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
// For license information, please see license.txt

frappe.query_reports["Stock Balance"] = {
	filters: [
		{
			fieldname: "qty_field",
			label: __("Stock Qty or Contents Qty"),
			fieldtype: "Select",
			options: "Stock Qty\nContents Qty",
			default: "Stock Qty"
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today()
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
			options: "Warehouse",
			get_query: () => {
				let warehouse_type = frappe.query_report.get_filter_value("warehouse_type");
				if (warehouse_type) {
					return {
						filters: {
							"warehouse_type": warehouse_type
						}
					};
				}
			}
		},
		{
			fieldname: "warehouse_type",
			label: __("Warehouse Type"),
			fieldtype: "Link",
			options: "Warehouse Type"
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
			fieldname: "include_uom",
			label: __("Include UOM"),
			fieldtype: "Link",
			options: "UOM"
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
		{
			fieldname: "show_zero_qty_rows",
			label: __("Show Zero Qty Rows"),
			fieldtype: "Check",
		},
		{
			fieldname: "show_returns_separately",
			label: __("Show Returns Separately"),
			fieldtype: "Check"
		},
		{
			fieldname: "show_projected_qty",
			label: __("Show Projected Qty"),
			fieldtype: "Check"
		},
		{
			fieldname: "show_stock_ageing_data",
			label: __("Show Stock Ageing Data"),
			fieldtype: "Check"
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
