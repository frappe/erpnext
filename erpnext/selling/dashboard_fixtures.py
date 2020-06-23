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
		"name": "Selling",
		"dashboard_name": "Selling",
		"charts": [
			{ "chart": "Sales Order Trends", "width": "Full"},
			{ "chart": "Top Customers", "width": "Half"},
			{ "chart": "Sales Order Analysis", "width": "Half"},
			{ "chart": "Item-wise Annual Sales", "width": "Full"}
		],
		"cards": [
			{ "card": "Annual Sales"},
			{ "card": "Sales Orders to Deliver"},
			{ "card": "Sales Orders to Bill"},
			{ "card": "Active Customers"}
		]
	}]

def get_charts():
	return [
		{
			"name": "Sales Order Analysis",
			"chart_name": _("Sales Order Analysis"),
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
			"report_name": "Sales Order Analysis",
			"type": "Donut"
		},
		{
			"name": "Item-wise Annual Sales",
			"chart_name": _("Item-wise Annual Sales"),
			"chart_type": "Report",
			"doctype": "Dashboard Chart",
			"filters_json": json.dumps({
				"company": company.name,
				"from_date": start_date,
				"to_date": end_date
			}),
			"is_custom": 1,
			"is_public": 1,
			"owner": "Administrator",
			"report_name": "Item-wise Sales History",
			"type": "Bar"
		},
		{
			"name": "Sales Order Trends",
			"chart_name": _("Sales Order Trends"),
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
				"based_on": "Item"
			}),
			"is_custom": 1,
			"is_public": 1,
			"owner": "Administrator",
			"report_name": "Sales Order Trends",
			"type": "Line"
		},
		{
			"name": "Top Customers",
			"chart_name": _("Top Customers"),
			"chart_type": "Report",
			"doctype": "Dashboard Chart",
			"filters_json": json.dumps({
				"company": company.name,
				"period": "Monthly",
				"fiscal_year": fiscal_year_name,
				"based_on": "Customer"
			}),
			"is_custom": 1,
			"is_public": 1,
			"owner": "Administrator",
			"report_name": "Delivery Note Trends",
			"type": "Bar"
		}
 	]

def get_number_cards():
	return [
		{
			"name": "Annual Sales",
			"aggregate_function_based_on": "base_net_total",
			"doctype": "Number Card",
			"document_type": "Sales Order",
			"filters_json": json.dumps([
				["Sales Order", "transaction_date", "Between", [start_date, end_date], False],
				["Sales Order", "status", "not in", ["Draft", "Cancelled", "Closed", None], False],
				["Sales Order", "docstatus", "=", 1, False],
				["Sales Order", "company", "=", company.name, False]
			]),
			"function": "Sum",
			"is_public": 1,
			"label": _("Annual Sales"),
			"owner": "Administrator",
			"show_percentage_stats": 1,
			"stats_time_interval": "Monthly"
		},
		{
			"name": "Sales Orders to Deliver",
			"doctype": "Number Card",
			"document_type": "Sales Order",
			"filters_json": json.dumps([
				["Sales Order", "status", "in", ["To Deliver and Bill", "To Deliver", None], False],
				["Sales Order", "docstatus", "=", 1, False],
				["Sales Order", "company", "=", company.name, False]
			]),
			"function": "Count",
			"is_public": 1,
			"label": _("Sales Orders to Deliver"),
			"owner": "Administrator",
			"show_percentage_stats": 1,
			"stats_time_interval": "Weekly"
		},
		{
			"name": "Sales Orders to Bill",
			"doctype": "Number Card",
			"document_type": "Sales Order",
			"filters_json": json.dumps([
				["Sales Order", "status", "in", ["To Deliver and Bill", "To Bill", None], False],
				["Sales Order", "docstatus", "=", 1, False],
				["Sales Order", "company", "=", company.name, False]
			]),
			"function": "Count",
			"is_public": 1,
			"label": _("Sales Orders to Bill"),
			"owner": "Administrator",
			"show_percentage_stats": 1,
			"stats_time_interval": "Weekly"
		},
		{
			"name": "Active Customers",
			"doctype": "Number Card",
			"document_type": "Customer",
			"filters_json": json.dumps([["Customer", "disabled", "=", "0"]]),
			"function": "Count",
			"is_public": 1,
			"label": "Active Customers",
			"owner": "Administrator",
			"show_percentage_stats": 1,
			"stats_time_interval": "Monthly"
		}
	]