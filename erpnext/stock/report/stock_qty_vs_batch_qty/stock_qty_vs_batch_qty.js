// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Stock Qty vs Batch Qty"] = {
	filters: [
		{
			fieldname: "item",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
			get_query: function () {
				return {
					filters: { has_batch_no: true },
				};
			},
		},
		{
			fieldname: "batch",
			label: __("Batch"),
			fieldtype: "Link",
			options: "Batch",
			get_query: function () {
				const item_code = frappe.query_report.get_filter_value("item");
				return {
					filters: { item: item_code, disabled: 0 },
				};
			},
		},
	],
	onload: function (report) {
		report.page.add_inner_button(__("Update Batch Qty"), function () {
			let indexes = frappe.query_report.datatable.rowmanager.getCheckedRows();
			let selected_rows = indexes
				.map((i) => frappe.query_report.data[i])
				.filter((row) => row.difference != 0);

			if (selected_rows.length) {
				frappe.call({
					method: "erpnext.stock.report.stock_qty_vs_batch_qty.stock_qty_vs_batch_qty.update_batch_qty",
					args: {
						selected_batches: selected_rows,
					},
					callback: function (r) {
						if (!r.exc) {
							report.refresh();
						}
					},
				});
			} else {
				frappe.msgprint(__("Please select at least one row with difference value"));
			}
		});
	},

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname == "difference" && data) {
			if (data.difference > 0) {
				value = "<span style='color:red'>" + value + "</span>";
			} else if (data.difference < 0) {
				value = "<span style='color:red'>" + value + "</span>";
			}
		}
		return value;
	},
	get_datatable_options(options) {
		return Object.assign(options, {
			checkboxColumn: true,
		});
	},
};
