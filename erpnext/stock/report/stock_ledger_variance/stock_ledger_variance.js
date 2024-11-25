// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

const DIFFERENCE_FIELD_NAMES = [
	"difference_in_qty",
	"fifo_qty_diff",
	"fifo_value_diff",
	"fifo_valuation_diff",
	"valuation_diff",
	"fifo_difference_diff",
	"diff_value_diff",
];

frappe.query_reports["Stock Ledger Variance"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "item_code",
			fieldtype: "Link",
			label: __("Item"),
			options: "Item",
			get_query: function () {
				return {
					filters: { is_stock_item: 1, has_serial_no: 0 },
				};
			},
		},
		{
			fieldname: "warehouse",
			fieldtype: "Link",
			label: __("Warehouse"),
			options: "Warehouse",
			get_query: function () {
				return {
					filters: { is_group: 0, disabled: 0 },
				};
			},
		},
		{
			fieldname: "difference_in",
			fieldtype: "Select",
			label: __("Difference In"),
			options: [
				{
					// Check "Stock Ledger Invariant Check" report with A - B column
					label: __("Quantity (A - B)"),
					value: "Qty",
				},
				{
					// Check "Stock Ledger Invariant Check" report with G - D column
					label: __("Value (G - D)"),
					value: "Value",
				},
				{
					// Check "Stock Ledger Invariant Check" report with I - K column
					label: __("Valuation (I - K)"),
					value: "Valuation",
				},
			],
		},
		{
			fieldname: "include_disabled",
			fieldtype: "Check",
			label: __("Include Disabled"),
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (DIFFERENCE_FIELD_NAMES.includes(column.fieldname) && Math.abs(data[column.fieldname]) > 0.001) {
			value = "<span style='color:red'>" + value + "</span>";
		}

		return value;
	},

	get_datatable_options(options) {
		return Object.assign(options, {
			checkboxColumn: true,
		});
	},

	onload(report) {
		report.page.add_inner_button(__("Create Reposting Entries"), () => {
			let message = `
				<div>
					<p>
						Reposting Entries will change the value of
						accounts Stock In Hand, and Stock Expenses
						in the Trial Balance report and will also change
						the Balance Value in the Stock Balance report.
					</p>
					<p>Are you sure you want to create Reposting Entries?</p>
				</div>`;
			let indexes = frappe.query_report.datatable.rowmanager.getCheckedRows();
			let selected_rows = indexes.map((i) => frappe.query_report.data[i]);

			if (!selected_rows.length) {
				frappe.throw(__("Please select rows to create Reposting Entries"));
			}

			frappe.confirm(__(message), () => {
				frappe.call({
					method: "erpnext.stock.report.stock_ledger_invariant_check.stock_ledger_invariant_check.create_reposting_entries",
					args: {
						rows: selected_rows,
					},
				});
			});
		});
	},
};
