// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Total Stock Summary"] = {
	"filters": [
		{
			"fieldname":"group_by",
			"label": __("Group By"),
			"fieldtype": "Select",
			"width": "80",
			"reqd": 1,
			"options": ["", "Warehouse", "Company"],
			"change": function() {
				let group_by = frappe.query_report.get_filter_value("group_by")
				let company_filter = frappe.query_report.get_filter("company")
				if (group_by == "Company") {
					company_filter.df.reqd = 0;
					company_filter.df.hidden = 1;
					frappe.query_report.set_filter_value("company", "");
					company_filter.refresh();
				}
				else {
					company_filter.df.reqd = 1;
					company_filter.df.hidden = 0;
					company_filter.refresh();
					frappe.query_report.refresh();
				}
			}
		},
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"width": "80",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
	]
}
