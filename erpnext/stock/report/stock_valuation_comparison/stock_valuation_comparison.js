// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

const DIFFERENCE_FIELDS = [
	"qty_difference",
	"stock_value_difference_difference",
	"valuation_rate_difference",
	"stock_value_difference_in_balance",
];

frappe.query_reports["Stock Valuation Comparison"] = {
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
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "item_code",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
			get_query: function () {
				return {
					filters: { is_stock_item: 1 },
				};
			},
		},
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group",
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
			get_query: function () {
				return {
					filters: { company: frappe.query_report.get_filter_value("company") },
				};
			},
		},
		{
			fieldname: "show",
			label: __("Show"),
			fieldtype: "Select",
			options: [
				{
					label: __("First Difference per Item-Warehouse"),
					value: "First Difference per Item-Warehouse",
				},
				{ label: __("All Differences"), value: "All Differences" },
				{ label: __("All Entries"), value: "All Entries" },
			],
			default: "First Difference per Item-Warehouse",
		},
		{
			fieldname: "tolerance",
			label: __("Ignore Differences Below"),
			fieldtype: "Float",
			default: 0.01,
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (DIFFERENCE_FIELDS.includes(column.fieldname) && data && data[column.fieldname]) {
			value = `<span style="color: var(--red-500)">${value}</span>`;
		}

		return value;
	},
};
