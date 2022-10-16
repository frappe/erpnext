// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Committed Budget Report"] = {
	"filters": [
		/*{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		}, */
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
				}else{
					var cost_center = frappe.query_report.get_filter("cost_center"); cost_center.toggle(true);
					var project = frappe.query_report.get_filter("project"); project.toggle(false);		
				}
				// query_report.trigger_refresh();	
			},
			"reqd":1
		},
		{
			"fieldname": "project",
			"label": __("Project"),
			"fieldtype": "Link",
			"options": "Project",
			"get_query": function() {
				return {
					"doctype": "Project",
					"filters": {
						"status": "Open",
					}
				}
			}
		},
		{
			"fieldname": "cost_center",
			"label": __("Cost Center"),
			"fieldtype": "Link",
			"options": "Cost Center",
			"get_query": function() {return {'filters': [['Cost Center', 'disabled', '!=', '1']]}}
		},
	]
   }

