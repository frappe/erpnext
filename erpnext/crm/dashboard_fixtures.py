# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe, erpnext, json
from frappe import _

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
                { "chart": "Incoming Leads", "width": "Full" },
                { "chart": "Opportunity Trends", "width": "Full"},
                { "chart": "Won Opportunities", "width": "Full" },
                { "chart": "Territory Wise Opportunity Count", "width": "Half"},
                { "chart": "Opportunities via Campaigns", "width": "Half" },
                { "chart": "Territory Wise Sales", "width": "Full"},
                { "chart": "Lead Source", "width": "Half"}
            ],
            "cards": [
                { "card": "New Lead (Last 1 Month)" },
                { "card": "New Opportunity (Last 1 Month)" },
                { "card": "Won Opportunity (Last 1 Month)" },
                { "card": "Open Opportunity"},
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
        "name": "Incoming Leads",
        "doctype": "Dashboard Chart",
        "time_interval": "Yearly",
        "chart_type": "Count",
        "chart_name": _("Incoming Leads"),
        "timespan": "Last Quarter",
        "time_interval": "Weekly",
        "document_type": "Lead",
        "based_on": "creation",
        'is_public': 1,
        'timeseries': 1,
        "owner": "Administrator",
        "filters_json": json.dumps([]),
        "type": "Bar"
    },
    {
        "name": "Opportunity Trends",
        "doctype": "Dashboard Chart",
        "time_interval": "Yearly",
        "chart_type": "Count",
        "chart_name": _("Opportunity Trends"),
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
        "name": "Opportunities via Campaigns",
        "chart_name": _("Opportunities via Campaigns"),
        "doctype": "Dashboard Chart",
        "chart_type": "Group By",
        "group_by_type": "Count",
        "group_by_based_on": "campaign",
        "document_type": "Opportunity",
        'is_public': 1,
        'timeseries': 1,
        "owner": "Administrator",
        "filters_json": json.dumps([["Opportunity", "company", "=", company, False]]),
        "type": "Pie",
        "custom_options": json.dumps({
            "truncateLegends": 1,
            "maxSlices": 8
        })
    },
    {
        "name": "Won Opportunities",
        "doctype": "Dashboard Chart",
        "time_interval": "Yearly",
        "chart_type": "Count",
        "chart_name": _("Won Opportunities"),
        "timespan": "Last Year",
        "time_interval": "Monthly",
        "document_type": "Opportunity",
        "based_on": "modified",
        'is_public': 1,
        'timeseries': 1,
        "owner": "Administrator",
        "filters_json": json.dumps([
            ["Opportunity", "company", "=", company, False],
            ["Opportunity", "status", "=", "Converted", False]]),
        "type": "Bar"
    },
    {
        "name": "Territory Wise Opportunity Count",
        "doctype": "Dashboard Chart",
        "chart_type": "Group By",
        "group_by_type": "Count",
        "group_by_based_on": "territory",
        "chart_name": _("Territory Wise Opportunity Count"),
        "document_type": "Opportunity",
        'is_public': 1,
        "filters_json": json.dumps([
            ["Opportunity", "company", "=", company, False]
        ]),
        "owner": "Administrator",
        "type": "Donut",
        "custom_options": json.dumps({
            "truncateLegends": 1,
            "maxSlices": 8
        })
    },
    {
        "name": "Territory Wise Sales",
        "doctype": "Dashboard Chart",
        "chart_type": "Group By",
        "group_by_type": "Sum",
        "group_by_based_on": "territory",
        "chart_name": _("Territory Wise Sales"),
        "aggregate_function_based_on": "opportunity_amount",
        "document_type": "Opportunity",
        'is_public': 1,
        "owner": "Administrator",
        "filters_json": json.dumps([
            ["Opportunity", "company", "=", company, False],
            ["Opportunity", "status", "=", "Converted", False]
        ]),
        "type": "Bar"
    },
    {
        "name": "Lead Source",
        "doctype": "Dashboard Chart",
        "chart_type": "Group By",
        "group_by_type": "Count",
        "group_by_based_on": "source",
        "chart_name": _("Lead Source"),
        "document_type": "Lead",
        'is_public': 1,
        "owner": "Administrator",
        "type": "Pie",
        "custom_options": json.dumps({
            "truncateLegends": 1,
            "maxSlices": 8
        })
    }]

def get_number_cards():
	return [{
        "doctype": "Number Card",
        "document_type": "Lead",
        "name": "New Lead (Last 1 Month)",
        "filters_json": json.dumps([["Lead","creation","Previous","1 month",False]]),
        "function": "Count",
        "is_public": 1,
        "label": _("New Lead (Last 1 Month)"),
        "show_percentage_stats": 1,
        "stats_time_interval": "Daily"
    },
    {
        "doctype": "Number Card",
        "document_type": "Opportunity",
        "name": "New Opportunity (Last 1 Month)",
        "filters_json": json.dumps([["Opportunity","creation","Previous","1 month",False]]),
        "function": "Count",
        "is_public": 1,
        "label": _("New Opportunity (Last 1 Month)"),
        "show_percentage_stats": 1,
        "stats_time_interval": "Daily"
    },
    {
        "doctype": "Number Card",
        "document_type": "Opportunity",
        "name": "Won Opportunity (Last 1 Month)",
        "filters_json": json.dumps([["Opportunity","creation","Previous","1 month",False]]),
        "function": "Count",
        "is_public": 1,
        "label": _("Won Opportunity (Last 1 Month)"),
        "show_percentage_stats": 1,
        "stats_time_interval": "Daily"
    },
    {
        "doctype": "Number Card",
        "document_type": "Opportunity",
        "name": "Open Opportunity",
        "filters_json": json.dumps([["Opportunity","status","=","Open",False]]),
        "function": "Count",
        "is_public": 1,
        "label": _("Open Opportunity"),
        "show_percentage_stats": 1,
        "stats_time_interval": "Daily"
    }] 