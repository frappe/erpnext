// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

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
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "sales_person",
			label: __("Sales Person"),
			fieldtype: "Link",
			options: "Sales Person"
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
			fieldname: "exclude_unpaid_invoices",
			label: __("Exclude Unpaid Invoices"),
			fieldtype: "Check",
		},
		{
			fieldname: "show_deduction_details",
			label: __("Show Deduction Details"),
			fieldtype: "Check",
		}
	],

	formatter: function (value, row, column, data, default_formatter) {
		var style = {};

		if (column.fieldname == "allocated_amount") {
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

		if (data && flt(data.base_net_total) < 0 && ['name', 'base_net_total', 'allocated_amount', 'grand_total'].includes(column.fieldname)) {
			style['color'] = 'red';
		}

		return default_formatter(value, row, column, data, {css: style});
	}
}
