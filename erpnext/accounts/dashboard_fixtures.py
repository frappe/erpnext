# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
import json
from frappe.utils import nowdate, add_months
from frappe import _
from erpnext.accounts.utils import get_fiscal_year

def get_company_for_dashboards():
	company = frappe.defaults.get_defaults().company
	if company:
		return company
	else:
		company_list = frappe.get_list("Company")
		if company_list:
			return company_list[0].name
	return None

def get_data():
	return frappe._dict({
		"dashboards": get_dashboards(),
		"charts": get_charts(),
		"number_cards": get_number_cards()
	})

def get_dashboards():
	return [{
		"name": "Accounts Dashboard",
		"dashboard_name": "Accounts",
		"doctype": "Dashboard",
		"charts": [
			{ "chart": "Profit and Loss" , "width": "Full"},
			{ "chart": "Incoming Bills"},
			{ "chart": "Outgoing Bills"},
			{ "chart": "Accounts Receivable Ageing"},
			{ "chart": "Accounts Payable Ageing"},
			{ "chart": "Budget Variance", "width": "Full"},
			{ "chart": "Bank Balance", "width": "Full"},
		],
		"cards": [
			{"card": "Total Payment Received"}
		]
	}]

def get_charts():
	company = frappe.get_doc("Company", get_company_for_dashboards())
	bank_account = company.default_bank_account or get_account("Bank", company.name)
	fiscal_year = get_fiscal_year(date=nowdate())
	default_cost_center = company.cost_center

	return [
		{
			"doctype": "Dashboard Charts",
			"name": "Profit and Loss",
			"owner": "Administrator",
			"report_name": "Profit and Loss Statement",
			"filters_json": json.dumps({
				"company": company.name,
				"filter_based_on": "Date Range",
				"period_start_date": add_months(nowdate(), -4),
				"period_end_date": nowdate(),
				"periodicity": "Monthly",
				"include_default_book_entries": 1
				}),
			"type": "Bar",
			'timeseries': 0,
			"chart_type": "Report",
			"chart_name": _("Profit and Loss"),
			"is_custom": 1
		},
		{
			"doctype": "Dashboard Chart",
			"time_interval": "Monthly",
			"name": "Incoming Bills",
			"chart_name": _("Incoming Bills (Purchase Invoice)"),
			"timespan": "Last Year",
			"color": "#a83333",
			"value_based_on": "base_grand_total",
			"filters_json": json.dumps({}),
			"chart_type": "Sum",
			"timeseries": 1,
			"based_on": "posting_date",
			"owner": "Administrator",
			"document_type": "Purchase Invoice",
			"type": "Bar",
			"width": "Half"
		},
		{
			"doctype": "Dashboard Chart",
			"name": "Outgoing Bills",
			"time_interval": "Monthly",
			"chart_name": _("Outgoing Bills (Sales Invoice)"),
			"timespan": "Last Year",
			"color": "#7b933d",
			"value_based_on": "base_grand_total",
			"filters_json": json.dumps({}),
			"chart_type": "Sum",
			"timeseries": 1,
			"based_on": "posting_date",
			"owner": "Administrator",
			"document_type": "Sales Invoice",
			"type": "Bar",
			"width": "Half"
		},
		{
			"doctype": "Dashboard Charts",
			"name": "Accounts Receivable Ageing",
			"owner": "Administrator",
			"report_name": "Accounts Receivable",
			"filters_json": json.dumps({
				"company": company.name,
				"report_date": nowdate(),
				"ageing_based_on": "Due Date",
				"range1": 30,
				"range2": 60,
				"range3": 90,
				"range4": 120
				}),
			"type": "Donut",
			'timeseries': 0,
			"chart_type": "Report",
			"chart_name": _("Accounts Receivable Ageing"),
			"is_custom": 1
		},
		{
			"doctype": "Dashboard Charts",
			"name": "Accounts Payable Ageing",
			"owner": "Administrator",
			"report_name": "Accounts Payable",
			"filters_json": json.dumps({
				"company": company.name,
				"report_date": nowdate(),
				"ageing_based_on": "Due Date",
				"range1": 30,
				"range2": 60,
				"range3": 90,
				"range4": 120
			}),
			"type": "Donut",
			'timeseries': 0,
			"chart_type": "Report",
			"chart_name": _("Accounts Payable Ageing"),
			"is_custom": 1
		},
		{
			"doctype": "Dashboard Charts",
			"name": "Budget Variance",
			"owner": "Administrator",
			"report_name": "Budget Variance Report",
			"filters_json": json.dumps({
				"company": company.name,
				"from_fiscal_year": fiscal_year[0],
				"to_fiscal_year": fiscal_year[0],
				"period": "Monthly",
				"budget_against": "Cost Center"
			}),
			"type": "Bar",
			"timeseries": 0,
			"chart_type": "Report",
			"chart_name": _("Budget Variance"),
			"is_custom": 1
		},
		{
			"doctype": "Dashboard Charts",
			"name": "Bank Balance",
			"time_interval": "Quarterly",
			"chart_name": "Bank Balance",
			"timespan": "Last Year",
			"filters_json": json.dumps({"company": company.name, "account": bank_account}),
			"source": "Account Balance Timeline",
			"chart_type": "Custom",
			"timeseries": 1,
			"owner": "Administrator",
			"type": "Line",
			"width": "Half"
		},
	]

def get_number_cards():
	return [
		{
			"doctype": "Number Card",
			"document_type": "Payment Entry",
			"name": "Total Payment Received",
			"filters_json": json.dumps([]),
			"label": _("Total Payment Received"),
			"function": "Sum",
			"aggregate_function_based_on": "base_received_amount",
			"is_public": 1,
			"is_custom": 1,
			"show_percentage_stats": 1,
			"stats_time_interval": "Daily"
		}
	]
