// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Production Progress Report"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": ("Company"),
			"fieldtype": "Link",
 			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname": "cost_center",
			"label": ("Cost Center"),
			"fieldtype": "Link",
 			"options": "Cost Center",
			"get_query": function() {
				var company = frappe.query_report.get_filter_value("company");
				return {
					'doctype': "Cost Center",
					'filters': [
						['disabled', '!=', '1'], 
						['company', '=', company]
					]
				}
			},
			"on_change": function(query_report) {
				var cost_center = query_report.get_filter_value("cost_center");
				if (!cost_center) {
					query_report.set_filter_value("branch","");
					query_report.refresh();
					return;
				}
				frappe.call({
					method: "erpnext.custom_utils.get_branch_from_cost_center",
					args: {
						"cost_center": cost_center,
					},
					callback: function(r) {
						query_report.set_filter_value("branch",r.message);
						query_report.refresh();
					}
				})
			},
			"reqd": 1,
		},
		{
			"fieldname": "branch",
			"label": ("Branch"),
			"fieldtype": "Link",
 			"options": "Branch",
			"read_only": 1,
			"get_query": function() {
				var company = frappe.query_report.get_filter_value("company");
				return {"doctype": "Branch", "filters": {"company": company, "is_disabled": 0}}
			}
		},
		{
			"fieldname": "fiscal_year",
			"label": ("Fiscal Year"),
			"fieldtype": "Link",
 			"options": "Fiscal Year",
			"reqd": 1
		},
		{
			"fieldname": "report_period",
			"label": ("Report Period"),
			"fieldtype": "Link",
 			"options": "Report Period",
			"reqd": 1
		},
		{
			"fieldname": "production_group",
			"label": ("Material Code"),
			"fieldtype": "Link",
 			"options": "Item",
			"reqd": 1,
			"is_production_item": 1
		},
		{
			"fieldname": "cumulative",
			"label": "Cumulative",
			"fieldtype": "Check",
			"default": 0
		}
	]
};
