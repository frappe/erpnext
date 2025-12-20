// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Financial Ratios"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "from_fiscal_year",
			label: __("Start Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today()),
			reqd: 1,
		},
		{
			fieldname: "to_fiscal_year",
			label: __("End Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today()),
			reqd: 1,
		},
		{
			fieldname: "periodicity",
			label: __("Periodicity"),
			fieldtype: "Data",
			default: "Yearly",
			reqd: 1,
			hidden: 1,
		},
		{
			fieldname: "period_start_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[1],
			hidden: 1,
		},
		{
			fieldname: "period_end_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[2],
			hidden: 1,
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		let heading_ratios = [__("Liquidity Ratios"), __("Solvency Ratios"), __("Turnover Ratios")];

		if (heading_ratios.includes(value)) {
			value = $(`<span>${value}</span>`);
			let $value = $(value).css("font-weight", "bold");
			value = $value.wrap("<p></p>").parent().html();
		}

		if (heading_ratios.includes(row[1]?.content) && column.fieldtype == "Float") {
			column.fieldtype = "Data";
		}

		value = default_formatter(value, row, column, data);

		return value;
	},
};
