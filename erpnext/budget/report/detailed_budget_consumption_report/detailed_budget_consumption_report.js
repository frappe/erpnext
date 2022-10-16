// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */
// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Detailed Budget Consumption Report"] = {
	"filters": [
			{
				"fieldname": "fiscal_year",
				"label": __("Fiscal Year"),
				"fieldtype": "Link",
				"options": "Fiscal Year",
				"default": frappe.defaults.get_user_default("fiscal_year"),
				"reqd": 1,
				"on_change": function(query_report) {
					var fiscal_year = query_report.get_values().fiscal_year;
					if (!fiscal_year) {
						return;
					}
					frappe.model.with_doc("Fiscal Year", fiscal_year, function(r) {
						var fy = frappe.model.get_doc("Fiscal Year", fiscal_year);
						query_report.filters_by_name.from_date.set_input(fy.year_start_date);
						query_report.filters_by_name.to_date.set_input(fy.year_end_date);
						query_report.trigger_refresh();
					});
				}
			},
			{
				"fieldname": "from_date",
				"label": __("From Date"),
				"fieldtype": "Date",
				"default": frappe.defaults.get_user_default("year_start_date"),
			},
			{
				"fieldname": "to_date",
				"label": __("To Date"),
				"fieldtype": "Date",
				"default": frappe.defaults.get_user_default("year_end_date"),
			},
			{
				"fieldname":"budget_against",
				"label": __("Budget Against"),
				"fieldtype": "Select",
				"options": ["", __("Cost Center"), __("Project")],
				on_change: function(query_report){
					var budget_against = frappe.query_report.get_filter_value('budget_against');
					if(budget_against == "Project"){
						var cost_center = frappe.query_report.get_filter("cost_center"); cost_center.toggle(false);
						var project = frappe.query_report.get_filter("project"); project.toggle(true);
						var budget_type = frappe.query_report.get_filter("budget_type"); budget_type.toggle(false);	
					}else if (budget_against == "Cost Center"){
						var cost_center = frappe.query_report.get_filter("cost_center"); cost_center.toggle(true);
						var project = frappe.query_report.get_filter("project"); project.toggle(false);	
						var budget_type = frappe.query_report.get_filter("budget_type"); budget_type.toggle(true);			
					}else{
						var cost_center = frappe.query_report.get_filter("cost_center"); cost_center.toggle(false);
						var project = frappe.query_report.get_filter("project"); project.toggle(false);	
						var budget_type = frappe.query_report.get_filter("budget_type"); budget_type.toggle(false);	
					}
					query_report.refresh();	
				},
				"reqd":1
			},
			{
				"fieldname": "project",
				"label": __("Project"),
				"fieldtype": "Link",
				"options": "Project",
				/*
				"get_query": function() {
					var fiscal_year = frappe.query_report.get_filter_value('fiscal_year');
					return {
						"doctype": "Project",
						"filters": {
							"fiscal_year": fiscal_year,
						}
					}
				}*/
			},
			{
				"fieldname": "cost_center",
				"label": __("Cost Center"),
				"fieldtype": "Link",
				"options": "Cost Center",
				"get_query": function() {return {'filters': [['Cost Center','disabled', '!=', '1'],['Cost Center','is_group', 'in', ['0','1']]]}}
			},
			{
				"fieldname": "budget_type",
				"label": __("Budget Type"),
				"fieldtype": "Link",
				"options": "Budget Type",
				"ignore_user_permissions":1
			},
			{
				"fieldname": "account",
				"label": __("Account"),
				"fieldtype": "Link",
				"options": "Account"
			},
			{
				"fieldname": "voucher_no",
				"label": __("Voucher No"),
				"fieldtype": "Data"
			},
	],
	onload: function(report) {
		report.page.add_inner_button(__("Budget Consumption Report"), function() {
			var filters = report.get_values();
			frappe.route_options = {
				"budget_against": filters.budget_against,
				"cost_center": filters.cost_center,
				"project": filters.project,
				"budget_type": filters.budget_type,
			};
			frappe.set_route('query-report', 'Budget Consumption Report');
		});
	}
};
