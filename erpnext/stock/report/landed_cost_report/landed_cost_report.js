// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Landed Cost Report"] = {
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
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
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
			fieldname: "raw_material_voucher_type",
			label: __("Raw Material Voucher Type"),
			fieldtype: "Select",
			options: "\nPurchase Receipt\nPurchase Invoice\nStock Entry\nSubcontracting Receipt",
		},
		{
			fieldname: "raw_material_voucher_no",
			label: __("Raw Material Voucher No"),
			fieldtype: "Dynamic Link",
			get_options: function () {
				let voucher_type = frappe.query_report.get_filter_value("raw_material_voucher_type");
				return voucher_type;
			},
			get_query: function () {
				let company = frappe.query_report.get_filter_value("company");
				let voucher_type = frappe.query_report.get_filter_value("raw_material_voucher_type");
				let query_filters = {
					docstatus: 1,
					company: company,
				};

				if (voucher_type === "Purchase Invoice") {
					query_filters["update_stock"] = 1;
				}

				return {
					filters: query_filters,
				};
			},
		},
	],
};
