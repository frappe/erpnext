// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

const DIFFERNCE_FIELD_NAMES = [
	"difference_in_qty",
	"fifo_qty_diff",
	"fifo_value_diff",
	"fifo_valuation_diff",
	"valuation_diff",
	"fifo_difference_diff",
	"diff_value_diff"
];

frappe.query_reports["Stock Ledger Invariant Check"] = {
	"filters": [
		{
			"fieldname": "item_code",
			"fieldtype": "Link",
			"label": "Item",
			"mandatory": 1,
			"options": "Item",
			get_query: function() {
				return {
					filters: {is_stock_item: 1, has_serial_no: 0}
				}
			}
		},
		{
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"label": "Warehouse",
			"mandatory": 1,
			"options": "Warehouse",
		}
	],
	formatter (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (DIFFERNCE_FIELD_NAMES.includes(column.fieldname) && Math.abs(data[column.fieldname]) > 0.001) {
			value = "<span style='color:red'>" + value + "</span>";
		}
		return value;
	},
};
