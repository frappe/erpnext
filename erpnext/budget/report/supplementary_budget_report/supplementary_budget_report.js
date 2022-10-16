// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Supplementary Budget Report"] = {
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
				var budget_against = query_report.get_filter_value('budget_against');
				if(budget_against == "Project"){
					var to_acc = query_report.get_filter("to_acc"); to_acc.toggle(false);
					//to_acc.refresh();
					var to_project = query_report.get_filter("to_project"); to_project.toggle(true);
					//to_project.refresh();
				}else{
					var to_acc= query_report.get_filter("to_acc");
					to_acc.toggle(true);
					//to_acc.refresh();
					var to_project= query_report.get_filter("to_project");
					to_project.toggle(false);
					//to_project.refresh();
				}
				query_report.trigger_refresh();

			}
		},
		{
			"fieldname": "to_project",
			"label": __("To Project"),
			"fieldtype": "Link",
			"options": "Project",
		},
		{
			"fieldname": "to_cc",
			"label": __("To Cost Center"),
			"fieldtype": "Link",
			"options": "Cost Center",
		},
		{
			"fieldname": "to_acc",
			"label": __("To Account"),
			"fieldtype": "Link",
			"options": "Account",
		},
	]
}