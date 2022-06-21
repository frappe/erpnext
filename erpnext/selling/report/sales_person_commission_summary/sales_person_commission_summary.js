// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

const group_by_options_spcs = [
	"Ungrouped", "Group by Sales Person", "Group by Territory", "Group by Sales Commission Category",
	"Group by Invoice", "Group by Customer"
]

frappe.query_reports["Sales Person Commission Summary"] = {
	"filters": [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "date_type",
			label: __("Which Date"),
			fieldtype: "Select",
			options: [
				'Invoice Date',
				'Clearing Date'
			],
			default: "Invoice Date",
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.defaults.get_user_default("year_start_date"),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.defaults.get_user_default("year_end_date"),
			reqd: 1,
		},
		{
			fieldname: "sales_person",
			label: __("Sales Person"),
			fieldtype: "Link",
			options: "Sales Person",
			bold: 1,
		},
		{
			fieldname: "territory",
			label: __("Territory"),
			fieldtype: "Link",
			options: "Territory",
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "name",
			label: __("Sales Invoice"),
			fieldtype: "Link",
			options: "Sales Invoice",
			filters: {
				"docstatus": 1,
			}
		},
		{
			fieldname: "sales_commission_category",
			label: __("Sales Commission Category"),
			fieldtype: "Link",
			options: "Sales Commission Category"
		},
		{
			fieldname: "transaction_type",
			label: __("Transaction Type"),
			fieldtype: "Link",
			options: "Transaction Type"
		},
		{
			fieldname: "cost_center",
			label: __("Cost Center"),
			fieldtype: "MultiSelectList",
			get_data: function(txt) {
				return frappe.db.get_link_options('Cost Center', txt, {
					company: frappe.query_report.get_filter_value("company")
				});
			}
		},
		{
			fieldname: "group_by_1",
			label: __("Group By Level 1"),
			fieldtype: "Select",
			options: group_by_options_spcs,
			default: "Ungrouped"
		},
		{
			fieldname: "group_by_2",
			label: __("Group By Level 2"),
			fieldtype: "Select",
			options: group_by_options_spcs,
			default: "Ungrouped"
		},
		{
			fieldname: "totals_only",
			label: __("Group Totals Only"),
			fieldtype: "Check",
			default: 0
		},
		{
			fieldname: "exclude_unpaid_invoices",
			label: __("Exclude Unpaid Invoices"),
			fieldtype: "Check",
		},
		{
			fieldname: "exclude_zero_commission",
			label: __("Exclude Zero Commission Rate"),
			fieldtype: "Check",
		},
		{
			fieldname: "show_deduction_details",
			label: __("Show Deduction Details"),
			fieldtype: "Check",
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		var style = {};

		if (["net_contribution_amount", "commission_amount"].includes(column.fieldname)) {
			style['font-weight'] = 'bold';
		}

		if (flt(value) && (column.fieldname == "total_deductions" || column.is_adjustment)) {
			style['color'] = 'orange';
		}

		if (flt(value) && column.fieldname == "outstanding_amount") {
			style['color'] = 'red';
		}

		if (flt(value) && column.fieldname == "paid_amount") {
			style['color'] = 'green';
		}

		if (flt(value) && column.fieldname == "return_amount") {
			style['color'] = 'orange';
		}

		if (value && flt(value) <= 0 && column.fieldname == "age") {
			style['color'] = 'blue';
		}

		if (flt(value) && column.fieldname == "late_payment_deduction_percent") {
			style['color'] = 'red';
		}

		if (data && flt(data.base_net_amount) < 0) {
			if (['name', 'base_net_amount', 'contribution_amount', 'net_contribution_amount', 'commission_amount',
					'base_grand_total'].includes(column.fieldname)) {
				style['color'] = 'red';
			}
		}

		return default_formatter(value, row, column, data, {css: style});
	},
	"initial_depth": 1,
}
