# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
import json
from frappe import _
from frappe.utils import nowdate
from erpnext.accounts.utils import get_fiscal_year

def get_data():
	return frappe._dict({
		"dashboards": get_dashboards(),
		"charts": get_charts(),
		"number_cards": get_number_cards(),
	})

def get_company_for_dashboards():
	company = frappe.defaults.get_defaults().company
	if company:
		return company
	else:
		company_list = frappe.get_list("Company")
		if company_list:
			return company_list[0].name
	return None

company = frappe.get_doc("Company", get_company_for_dashboards())
fiscal_year = get_fiscal_year(nowdate(), as_dict=1)
fiscal_year_name = fiscal_year.get("name")
start_date = str(fiscal_year.get("year_start_date"))
end_date = str(fiscal_year.get("year_end_date"))

def get_dashboards():
	return [{
		"name": "Buying",
		"dashboard_name": "Buying",
		"charts": [
			{ "chart": "Purchase Order Trends", "width": "Full"},
			{ "chart": "Material Request Analysis", "width": "Half"},
			{ "chart": "Purchase Order Analysis", "width": "Half"},
			{ "chart": "Top Suppliers", "width": "Full"}
		],
		"cards": [
			{ "card": "Annual Purchase"},
			{ "card": "Purchase Orders to Receive"},
			{ "card": "Purchase Orders to Bill"},
			{ "card": "Active Suppliers"}
		]
	}]

def get_charts():
	return [
		{
			"name": "Purchase Order Analysis",
			"chart_name": _("Purchase Order Analysis"),
			"chart_type": "Report",
			"custom_options": json.dumps({
				"type": "donut",
				"height": 300,
				"axisOptions": {"shortenYAxisNumbers": 1}
			}),
			"doctype": "Dashboard Chart",
			"filters_json": json.dumps({
				"company": company.name,
				"from_date": start_date,
				"to_date": end_date
			}),
			"is_custom": 1,
			"is_public": 1,
			"owner": "Administrator",
			"report_name": "Purchase Order Analysis",
			"type": "Donut"
		},
		{
			"name": "Material Request Analysis",
			"chart_name": _("Material Request Analysis"),
			"chart_type": "Group By",
			"custom_options": json.dumps({"height": 300}),
			"doctype": "Dashboard Chart",
			"document_type": "Material Request",
			"filters_json": json.dumps(
				[["Material Request", "status", "not in", ["Draft", "Cancelled", "Stopped", None], False],
				["Material Request", "material_request_type", "=", "Purchase", False],
				["Material Request", "company", "=", company.name, False],
				["Material Request", "docstatus", "=", 1, False],
				["Material Request", "transaction_date", "Between", [start_date, end_date], False]]
			),
			"group_by_based_on": "status",
			"group_by_type": "Count",
			"is_custom": 0,
			"is_public": 1,
			"number_of_groups": 0,
			"owner": "Administrator",
			"type": "Donut"
		},
		{
			"name": "Purchase Order Trends",
			"chart_name": _("Purchase Order Trends"),
			"chart_type": "Report",
			"custom_options": json.dumps({
				"type": "line",
				"axisOptions": {"shortenYAxisNumbers": 1},
				"tooltipOptions": {},
				"lineOptions": {
					"regionFill": 1
				}
			}),
			"doctype": "Dashboard Chart",
			"filters_json": json.dumps({
				"company": company.name,
				"period": "Monthly",
				"fiscal_year": fiscal_year_name,
				"period_based_on": "posting_date",
				"based_on": "Item"
			}),
			"is_custom": 1,
			"is_public": 1,
			"owner": "Administrator",
			"report_name": "Purchase Order Trends",
			"type": "Line"
		},
		{
			"name": "Top Suppliers",
			"chart_name": _("Top Suppliers"),
			"chart_type": "Report",
			"doctype": "Dashboard Chart",
			"filters_json": json.dumps({
				"company": company.name,
				"period": "Monthly",
				"fiscal_year": fiscal_year_name,
				"period_based_on": "posting_date",
				"based_on": "Supplier"
			}),
			"is_custom": 1,
			"is_public": 1,
			"owner": "Administrator",
			"report_name": "Purchase Receipt Trends",
			"type": "Bar"
		}
 	]

def get_number_cards():
	return [
		{
			"name": "Annual Purchase",
			"aggregate_function_based_on": "base_net_total",
			"doctype": "Number Card",
			"document_type": "Purchase Order",
			"filters_json": json.dumps([
				["Purchase Order", "transaction_date", "Between", [start_date, end_date], False],
				["Purchase Order", "status", "not in", ["Draft", "Cancelled", "Closed", None], False],
				["Purchase Order", "docstatus", "=", 1, False],
				["Purchase Order", "company", "=", company.name, False],
				["Purchase Order", "transaction_date", "Between", [start_date,end_date], False]
			]),
			"function": "Sum",
			"is_public": 1,
			"label": _("Annual Purchase"),
			"owner": "Administrator",
			"show_percentage_stats": 1,
			"stats_time_interval": "Monthly"
		},
		{
			"name": "Purchase Orders to Receive",
			"doctype": "Number Card",
			"document_type": "Purchase Order",
			"filters_json": json.dumps([
				["Purchase Order", "status", "in", ["To Receive and Bill", "To Receive", None], False],
				["Purchase Order", "docstatus", "=", 1, False],
				["Purchase Order", "company", "=", company.name, False]
			]),
			"function": "Count",
			"is_public": 1,
			"label": _("Purchase Orders to Receive"),
			"owner": "Administrator",
			"show_percentage_stats": 1,
			"stats_time_interval": "Weekly"
		},
		{
			"name": "Purchase Orders to Bill",
			"doctype": "Number Card",
			"document_type": "Purchase Order",
			"filters_json": json.dumps([
				["Purchase Order", "status", "in", ["To Receive and Bill", "To Bill", None], False],
				["Purchase Order", "docstatus", "=", 1, False],
				["Purchase Order", "company", "=", company.name, False]
			]),
			"function": "Count",
			"is_public": 1,
			"label": _("Purchase Orders to Bill"),
			"owner": "Administrator",
			"show_percentage_stats": 1,
			"stats_time_interval": "Weekly"
		},
		{
			"name": "Active Suppliers",
			"doctype": "Number Card",
			"document_type": "Supplier",
			"filters_json": json.dumps([["Supplier", "disabled", "=", "0"]]),
			"function": "Count",
			"is_public": 1,
			"label": "Active Suppliers",
			"owner": "Administrator",
			"show_percentage_stats": 1,
			"stats_time_interval": "Monthly"
		}
	]