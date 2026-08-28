// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Incorrect Balance Qty After Transaction"] = {
	filters: [
		{
			label: __("Company"),
			fieldtype: "Link",
			fieldname: "company",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			label: __("Item Code"),
			fieldtype: "Link",
			fieldname: "item_code",
			options: "Item",
		},
		{
			label: __("Warehouse"),
			fieldtype: "MultiSelectList",
			fieldname: "warehouse",
			options: "Warehouse",
			get_data: function (txt) {
				let company = frappe.query_report.get_filter_value("company");
				return frappe.db.get_link_options("Warehouse", txt, company ? { company } : {});
			},
		},
	],
};
