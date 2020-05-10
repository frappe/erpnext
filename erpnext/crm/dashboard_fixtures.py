# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe, erpnext, json

def get_data():
	return frappe._dict({
        "dashboards": get_dashboards(),
        "charts": get_charts(),
        "number_cards": get_number_cards()
	})

def get_dashboards():
	return [{
            "doctype": "Dashboard",
            "name": "CRM",
            "dashboard_name": "CRM",
            "charts": [
                { "chart": "Lead", "width": "Full" },
                { "chart": "Opportunity", "width": "Full"},
                { "chart": "Campaign", "width": "Half" },
                { "chart": "Opportunities Won", "width": "Half" },
                { "chart": "Territory Wise Opportunity", "width": "Half"},
                { "chart": "Territory Wise Sales", "width": "Half"},
                { "chart": "Qualified For Call", "width": "Full"},
                { "chart": "Lead Source", "width": "Half"}
            ],
            "cards": [
                { "card": "New Lead" },
                { "card": "New Opportunity" },
                { "card": "Won Opportunity" },
            ]
        }]

def get_company_for_dashboards():
	company = frappe.defaults.get_defaults().company
	if company:
		return company
	else:
		company_list = frappe.get_list("Company")
		if company_list:
			return company_list[0].name
	return None

def get_charts():
	company = get_company_for_dashboards()

	return [{
        "name": "Lead",
        "doctype": "Dashboard Chart",
        "time_interval": "Yearly",
        "chart_type": "Count",
        "chart_name": "Lead",
        "timespan": "Last Quarter",
        "time_interval": "Weekly",
        "document_type": "Lead",
        "based_on": "creation",
        'is_public': 1,
        'timeseries': 1,
        "owner": "Administrator",
        "filters_json": json.dumps([["Opportunity", "company", "=", company, False]]),
        "type": "Bar"
    },
    {
        "name": "Opportunity",
        "doctype": "Dashboard Chart",
        "time_interval": "Yearly",
        "chart_type": "Count",
        "chart_name": "Opportunity",
        "timespan": "Last Quarter",
        "time_interval": "Weekly",
        "document_type": "Opportunity",
        "based_on": "creation",
        'is_public': 1,
        'timeseries': 1,
        "owner": "Administrator",
        "filters_json": json.dumps([["Opportunity", "company", "=", company, False]]),
        "type": "Bar"
    },
    {
        "name": "Campaign",
        "doctype": "Dashboard Chart",
        "time_interval": "Yearly",
        "chart_type": "Count",
        "chart_name": "Campaign",
        "timespan": "Last Year",
        "time_interval": "Monthly",
        "document_type": "Campaign",
        "based_on": "creation",
        'is_public': 1,
        'timeseries': 1,
        "owner": "Administrator",
        "filters_json": json.dumps([["Opportunity", "company", "=", company, False]]),
        "type": "Line",
        "color": "#428b46"
    },
    {
        "name": "Opportunities Won",
        "doctype": "Dashboard Chart",
        "time_interval": "Yearly",
        "chart_type": "Count",
        "chart_name": "Opportunities Won",
        "timespan": "Last Year",
        "time_interval": "Monthly",
        "document_type": "Opportunity",
        "based_on": "modified",
        'is_public': 1,
        'timeseries': 1,
        "owner": "Administrator",
        "filters_json": json.dumps([["Opportunity", "company", "=", company, False],["Opportunity", "sales_stage", "=", "Converted", False]]),
        "type": "Bar"
    },
    {
        "name": "Territory Wise Opportunity",
        "doctype": "Dashboard Chart",
        "chart_type": "Group By",
        "group_by_type": "Count",
        "group_by_based_on": "territory",
        "chart_name": "Territory Wise Opportunity",
        "document_type": "Opportunity",
        'is_public': 1,
        "owner": "Administrator",
        "type": "Line"
    },
    {
        "name": "Territory Wise Sales",
        "doctype": "Dashboard Chart",
        "chart_type": "Group By",
        "group_by_type": "Sum",
        "group_by_based_on": "territory",
        "chart_name": "Territory Wise Sales",
        "aggregate_function_based_on": "opportunity_amount",
        "document_type": "Opportunity",
        'is_public': 1,
        "owner": "Administrator",
        "filters_json": json.dumps([["Opportunity", "company", "=", company, False],["Opportunity", "sales_stage", "=", "Converted", False]]),
        "type": "Bar",
        "color": "#7575ff"
    },
    {
        "name": "Qualified For Call",
        "doctype": "Dashboard Chart",
        "time_interval": "Yearly",
        "chart_type": "Count",
        "chart_name": "Qualified For Call",
        "timespan": "Last Quarter",
        "time_interval": "Weekly",
        "document_type": "Opportunity",
        "based_on": "modified",
        'is_public': 1,
        'timeseries': 1,
        "owner": "Administrator",
        "filters_json": json.dumps([["Opportunity", "company", "=", company, False],["Opportunity", "sales_stage", "=", "Qualification", False]]),
        "type": "Line",
        "color": "#fff168"
    },
    {
        "name": "Lead Source",
        "doctype": "Dashboard Chart",
        "chart_type": "Group By",
        "group_by_type": "Count",
        "group_by_based_on": "source",
        "chart_name": "Lead Source",
        "document_type": "Lead",
        'is_public': 1,
        "owner": "Administrator",
        "type": "Donut"
    }]

def get_number_cards():
	return [{
        "doctype": "Number Card",
        "document_type": "Lead",
        "name": "New Lead",
        "filters_json": json.dumps([["Lead","status","=","Lead",False]]),
        "function": "Count",
        "is_public": 1,
        "label": "New Lead",
        "show_percentage_stats": 1,
        "stats_time_interval": "Daily"
    },
    {
        "doctype": "Number Card",
        "document_type": "Opportunity",
        "name": "New Opportunity",
        "filters_json": json.dumps([["Opportunity","status","=","Open",False]]),
        "function": "Count",
        "is_public": 1,
        "label": "New Opportunity",
        "show_percentage_stats": 1,
        "stats_time_interval": "Daily"
    },
    {
        "doctype": "Number Card",
        "document_type": "Opportunity",
        "name": "Won Opportunity",
        "filters_json": json.dumps([["Opportunity","status","=","Converted",False]]),
        "function": "Count",
        "is_public": 1,
        "label": "Won Opportunity",
        "show_percentage_stats": 1,
        "stats_time_interval": "Daily"
    }] 