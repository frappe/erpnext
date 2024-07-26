// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Exponential Smoothing Forecasting"] = {
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
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), 12),
			reqd: 1,
		},
		{
			fieldname: "based_on_document",
			label: __("Based On Document"),
			fieldtype: "Select",
			options: ["Sales Order", "Sales Invoice", "Delivery Note", "Quotation"],
			default: "Sales Order",
			reqd: 1,
		},
		{
			fieldname: "based_on_field",
			label: __("Based On"),
			fieldtype: "Select",
			options: ["Qty", "Amount"],
			default: "Qty",
			reqd: 1,
		},
		{
			fieldname: "no_of_years",
			label: __("Based On Data ( in years )"),
			fieldtype: "Select",
			options: [3, 6, 9],
			default: 3,
			reqd: 1,
		},
		{
			fieldname: "periodicity",
			label: __("Periodicity"),
			fieldtype: "Select",
			options: [
				{ value: "Monthly", label: __("Monthly") },
				{ value: "Quarterly", label: __("Quarterly") },
				{ value: "Half-Yearly", label: __("Half-Yearly") },
				{ value: "Yearly", label: __("Yearly") },
			],
			default: "Yearly",
			reqd: 1,
		},
		{
			fieldname: "smoothing_constant",
			label: __("Smoothing Constant"),
			fieldtype: "Select",
			options: [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
			reqd: 1,
			default: 0.3,
		},
		{
			fieldname: "item_code",
			label: __("Item Code"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
			get_query: () => {
				var company = frappe.query_report.get_filter_value("company");
				if (company) {
					return {
						filters: {
							company: company,
						},
					};
				}
			},
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "item_code" && value.includes("Total Quantity")) {
			value = "<strong>" + value + "</strong>";
		}
		return value;
	},
};
