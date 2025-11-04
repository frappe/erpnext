// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

const DIFFERNCE_FIELD_NAMES = ["fifo_qty_diff", "fifo_value_diff"];

frappe.query_reports["FIFO Queue vs Qty After Transaction Comparison"] = {
	filters: [
		{
			fieldname: "item_code",
			fieldtype: "Link",
			label: "Item",
			options: "Item",
			get_query: function () {
				return {
					filters: { is_stock_item: 1, has_serial_no: 0 },
				};
			},
		},
		{
			fieldname: "item_group",
			fieldtype: "Link",
			label: "Item Group",
			options: "Item Group",
		},
		{
			fieldname: "warehouse",
			fieldtype: "Link",
			label: "Warehouse",
			options: "Warehouse",
		},
		{
			fieldname: "from_date",
			fieldtype: "Date",
			label: "From Posting Date",
		},
		{
			fieldname: "to_date",
			fieldtype: "Date",
			label: "From Posting Date",
		},
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (DIFFERNCE_FIELD_NAMES.includes(column.fieldname) && Math.abs(data[column.fieldname]) > 0.001) {
			value = "<span style='color:red'>" + value + "</span>";
		}
		return value;
	},
};
