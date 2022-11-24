// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Production Report"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": ("Company"),
			"fieldtype": "Link",
 			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1,
			"read_only":1
		},
		{
			"fieldname": "cost_center",
			"label": ("Cost Center"),
			"fieldtype": "Link",
 			"options": "Cost Center",
			"get_query": function() {
				var company = frappe.query_report.get_filter_value('company');
				return {
					'doctype': "Cost Center",
					'filters': [
						['disabled', '!=', '1'], 
						['company', '=', company]
					]
				}
			},
		},
		{
			"fieldname": "branch",
			"label": ("Branch"),
			"fieldtype": "Link",
 			"options": "Branch",
		},
		{
			"fieldname": "location",
			"label": ("Location"),
			"fieldtype": "Link",
 			"options": "Location",
			"get_query": function() {
				var branch = frappe.query_report.get_filter_value('branch');
				return {"doctype": "Location", "filters": {"branch": branch, "is_disabled": 0}}
			}
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.month_start(),
			"reqd": 1,
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.month_end(),
			"reqd": 1,
		},
		{
			"fieldname": "adhoc_production",
			"label": ("Adhoc Production"),
			"fieldtype": "Link",
 			"options": "Adhoc Production",
			"get_query": function() {
				var loc = frappe.query_report.get_filter_value('location');
				return {"doctype": "Adhoc Production", "filters": {"location": loc, "disabled": 0}}
			}
		},
		{
			"fieldname": "production_type",
			"label":("Production Type"),
			"fieldtype" : "Select",
			"width" :"80",
			"options": ["All", "Planned","Adhoc"],
			"default": "All",
			"reqd" : 1
		},
		{
			"fieldname": "item_group",
			"label": ("Item Group"),
			"fieldtype": "Link",
 			"options": "Item Group",
		},
		{
			"fieldname": "item",
			"label": ("Item"),
			"fieldtype": "Link",
 			"options": "Item",
		},
		{
			"fieldname": "warehouse",
			"label": ("Warehouse"),
			"fieldtype": "Link",
 			"options": "Warehouse",
		},
		{
			"fieldname": "show_aggregate",
			"label": ("Show Aggregate Data"),
			"fieldtype": "Check",
 			"default": 1,
		},
	]

};
