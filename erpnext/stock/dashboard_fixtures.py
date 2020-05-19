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
		"name": "Stock",
		"dashboard_name": "Stock",
		"charts": [
			{ "chart": "Warehouse wise Stock Value", "width": "Full"},
			{ "chart": "Purchase Receipt Trends", "width": "Half"},
			{ "chart": "Delivery Trends", "width": "Half"},
			{ "chart": "Oldest Items", "width": "Half"},
			{ "chart": "Item Shortage Summary", "width": "Half"}
		],
		"cards": [
			{ "card": "Total Active Items"},
			{ "card": "Total Warehouses"},
			{ "card": "Total Stock Value"}
		]
	}]

def get_charts():
	return [
		{
			"doctype": "Dashboard Chart",
			"name": "Purchase Receipt Trends",
			"time_interval": "Monthly",
			"chart_name": _("Purchase Receipt Trends"),
			"timespan": "Last Year",
			"color": "#7b933d",
			"value_based_on": "base_net_total",
			"filters_json": json.dumps([["Purchase Receipt", "docstatus", "=", 1]]),
			"chart_type": "Sum",
			"timeseries": 1,
			"based_on": "posting_date",
			"owner": "Administrator",
			"document_type": "Purchase Receipt",
			"type": "Bar",
			"width": "Half",
			"is_public": 1
		},
		{
			"doctype": "Dashboard Chart",
			"name": "Delivery Trends",
			"time_interval": "Monthly",
			"chart_name": _("Delivery Trends"),
			"timespan": "Last Year",
			"color": "#7b933d",
			"value_based_on": "base_net_total",
			"filters_json": json.dumps([["Delivery Note", "docstatus", "=", 1]]),
			"chart_type": "Sum",
			"timeseries": 1,
			"based_on": "posting_date",
			"owner": "Administrator",
			"document_type": "Delivery Note",
			"type": "Bar",
			"width": "Half",
			"is_public": 1
		},
		{
			"name": "Warehouse wise Stock Value",
			"chart_name": _("Warehouse wise Stock Value"),
			"chart_type": "Custom",
			"doctype": "Dashboard Chart",
			"filters_json": json.dumps({}),
			"is_custom": 0,
			"is_public": 1,
			"owner": "Administrator",
			"source": "Warehouse wise Stock Value",
			"type": "Bar"
		},
		{
			"name": "Oldest Items",
			"chart_name": _("Oldest Items"),
			"chart_type": "Report",
			"custom_options": json.dumps({
				"colors": ["#5e64ff"]
				}),
			"doctype": "Dashboard Chart",
			"filters_json": json.dumps({
				"company": company.name,
				"to_date": nowdate(),
				"show_warehouse_wise_stock": 0
			}),
			"is_custom": 1,
			"is_public": 1,
			"owner": "Administrator",
			"report_name": "Stock Ageing",
			"type": "Bar"
		},
		{
			"name": "Item Shortage Summary",
			"chart_name": _("Item Shortage Summary"),
			"chart_type": "Report",
			"doctype": "Dashboard Chart",
			"filters_json": json.dumps({
				"company": company.name
			}),
			"is_custom": 1,
			"is_public": 1,
			"owner": "Administrator",
			"report_name": "Item Shortage Report",
			"type": "Bar"
		}
	]

def get_number_cards():
	return [
		{
			"name": "Total Active Items",
			"label": _("Total Active Items"),
			"function": "Count",
			"doctype": "Number Card",
			"document_type": "Item",
			"filters_json": json.dumps([["Item", "disabled", "=", 0]]),
			"is_public": 1,
			"owner": "Administrator",
			"show_percentage_stats": 1,
			"stats_time_interval": "Monthly"
		},
		{
			"name": "Total Warehouses",
			"label": _("Total Warehouses"),
			"function": "Count",
			"doctype": "Number Card",
			"document_type": "Warehouse",
			"filters_json": json.dumps([["Warehouse", "disabled", "=", 0]]),
			"is_public": 1,
			"owner": "Administrator",
			"show_percentage_stats": 1,
			"stats_time_interval": "Monthly"
		},
		{
			"name": "Total Stock Value",
			"label": _("Total Stock Value"),
			"function": "Sum",
			"aggregate_function_based_on": "stock_value",
			"doctype": "Number Card",
			"document_type": "Bin",
			"filters_json": json.dumps([]),
			"is_public": 1,
			"owner": "Administrator",
			"show_percentage_stats": 1,
			"stats_time_interval": "Daily"
		}
	]