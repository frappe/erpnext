// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["HMRC VAT"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			filters: {
				country: "United Kingdom",
			},
		},
		{
			fieldname: "reporting_period",
			label: __("Reporting Period"),
			fieldtype: "Select",
			options: [
				{ value: "Annually", label: __("Yearly") },
				{ value: "Quarterly", label: __("Quarterly") },
				{ value: "Bi-Monthly", label: __("Bi-Monthly") },
				{ value: "Monthly", label: __("Monthly") },
			],
			default: "Quarterly",
		},
		{
			fieldname: "fiscal_year",
			label: __("Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today()),
			reqd: 1,
		},
		{
			fieldname: "period_start_month",
			label: __("Period Start Month"),
			fieldtype: "Select",
			options: [
				"January",
				"February",
				"March",
				"April",
				"May",
				"June",
				"July",
				"August",
				"September",
				"October",
				"November",
				"December",
			],
			default: "January",
			width: "80",
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		const styles = {
			0: "font-weight-bold", // bold box rows
			1: "font-weight-bold font-italic", // bold and italic rate rows
			2: "font-weight-normal", // normal invoice rows
			3: "small", // small item rows
		};
		const style = styles[data.indent ?? 0] || "";
		var $value = $(`<span>${value}</span>`).addClass(style);
		if (data.warn_if_negative && data[column.fieldname] < 0) {
			$value.addClass("text-danger");
		}
		value = $value.wrap("<p></p>").parent().html();
		return value;
	},

	tree: true,
	initial_depth: 2,
	name_field: "row_id",
	parent_field: "parent_row_id",
};
