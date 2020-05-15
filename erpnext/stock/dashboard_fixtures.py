# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
import json
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
fiscal_year = get_fiscal_year(nowdate(), as_dict=1).get("name")

def get_dashboards():
	return [{
		"name": "Stock",
		"dashboard_name": "Stock",
		"charts": [
			{ "chart": "Item Shortage Summary", "width": "Half"},
			{ "chart": "Stock Ageing", "width": "Half"},
			{ "chart": "Item Wise Annual Revenue", "width": "Half"},
			{ "chart": "Item Wise Annual Expenditure", "width": "Half"},
			{ "chart": "Warehouse wise Stock Value", "width": "Full"}
		],
		"cards": [
			{ "card": "Purchase Receipts to Bill"},
			{ "card": "Amount Payable against Receipt"},
			{ "card": "Delivery Notes to Bill"},
			{ "card": "Amount Receivable against Delivery"}
		]
	}]

def get_charts():
	return [
		{
			"name": "Item Shortage Summary",
			"chart_name": "Item Shortage Summary",
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
		},
		{
			"name": "Stock Ageing",
			"chart_name": "Stock Ageing",
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
			"name": "Item Wise Annual Revenue",
			"chart_name": "Item Wise Annual Revenue",
			"chart_type": "Report",
			"custom_options": json.dumps({
				"axisOptions": {"shortenYAxisNumbers": 1},
				"tooltipOptions": {},
				"colors":["#5e64ff"]
			}),
			"doctype": "Dashboard Chart",
			"filters_json": json.dumps({
				"period": "Monthly",
				"based_on": "Item",
				"fiscal_year": fiscal_year,
				"company": company.name
			}),
			"is_custom": 1,
			"is_public": 1,
			"owner": "Administrator",
			"report_name": "Delivery Note Trends",
			"type": "Bar"
		},
		{
			"name": "Item Wise Annual Expenditure",
			"chart_name": "Item Wise Annual Expenditure",
			"chart_type": "Report",
			"custom_options": json.dumps({
				"axisOptions": {"shortenYAxisNumbers": 1},
				"tooltipOptions": {},
				"colors":["#5e64ff"]
			}),
			"doctype": "Dashboard Chart",
			"filters_json": json.dumps({
				"period": "Monthly",
				"based_on": "Item",
				"fiscal_year": fiscal_year,
				"company": company.name,
				"period_based_on": "posting_date"
			}),
			"is_custom": 1,
			"is_public": 1,
			"owner": "Administrator",
			"report_name": "Purchase Receipt Trends",
			"type": "Bar"
		},
		{
			"name": "Warehouse wise Stock Value",
			"chart_name": "Warehouse wise Stock Value",
			"chart_type": "Custom",
			"doctype": "Dashboard Chart",
			"filters_json": json.dumps({}),
			"is_custom": 0,
			"is_public": 1,
			"owner": "Administrator",
			"source": "Warehouse wise Stock Value",
			"type": "Bar"
		}

	]

def get_number_cards():
	return [
		{
			"name": "Amount Payable against Receipt",
			"label": "Amount Payable against Receipt",
			"function": "Sum",
			"aggregate_function_based_on": "base_grand_total",
			"doctype": "Number Card",
			"document_type": "Purchase Receipt",
			"filters_json": json.dumps(
				[["Purchase Receipt","status","=","To Bill",False],
				["Purchase Receipt","company","=", company.name, False]]
			),
			"is_public": 1,
			"owner": "Administrator",
			"show_percentage_stats": 1,
			"stats_time_interval": "Daily"
		},
		{
			"name": "Amount Receivable against Delivery",
			"label": "Amount Receivable against Delivery",
			"function": "Sum",
			"aggregate_function_based_on": "base_grand_total",
			"doctype": "Number Card",
			"document_type": "Delivery Note",
			"filters_json": json.dumps(
				[["Delivery Note","company","=",company.name,False],
				["Delivery Note","status","=","To Bill",False]]
			),
			"is_public": 1,
			"owner": "Administrator",
			"show_percentage_stats": 1,
			"stats_time_interval": "Daily"
		},
		{
			"name": "Purchase Receipts to Bill",
			"label": "Purchase Receipts to Bill",
			"function": "Count",
			"doctype": "Number Card",
			"document_type": "Purchase Receipt",
			"filters_json": json.dumps(
				[["Purchase Receipt","status","=","To Bill",False],
				["Purchase Receipt","company","=", company.name, False]]
			),
			"is_public": 1,
			"owner": "Administrator",
			"show_percentage_stats": 1,
			"stats_time_interval": "Daily"
		},
		{
			"name": "Delivery Notes to Bill",
			"label": "Delivery Notes to Bill",
			"function": "Count",
			"doctype": "Number Card",
			"document_type": "Delivery Note",
			"filters_json": json.dumps(
				[["Delivery Note","company","=",company.name,False],
				["Delivery Note","status","=","To Bill",False]]
			),
			"is_public": 1,
			"owner": "Administrator",
			"show_percentage_stats": 1,
			"stats_time_interval": "Daily"
		}
	]