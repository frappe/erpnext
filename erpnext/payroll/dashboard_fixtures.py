# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
import erpnext
from erpnext.hr.dashboard_fixtures import get_dashboards_chart_doc, get_number_cards_doc
import json
from frappe import _

def get_data():
	return frappe._dict({
		"dashboards": get_dashboards(),
		"charts": get_charts(),
		"number_cards": get_number_cards(),
	})

def get_dashboards():
	dashboards = []
	dashboards.append(get_payroll_dashboard())
	return dashboards

def get_payroll_dashboard():
	return {
		"name": "Payroll",
		"dashboard_name": "Payroll",
		"is_default": 1,
		"charts": [
			{ "chart": "Outgoing Salary", "width": "Full"},
			{ "chart": "Designation Wise Salary(Last Month)", "width": "Half"},
			{ "chart": "Department Wise Salary(Last Month)", "width": "Half"},
		],
		"cards": [
			{"card": "Total Declaration Submitted"},
			{"card": "Total Salary Structure"},
			{"card": "Total Incentive Given(Last month)"},
			{"card": "Total Outgoing Salary(Last month)"},
		]
	}

def get_charts():
	dashboard_charts= [
		get_dashboards_chart_doc('Outgoing Salary', "Sum", "Line",
			document_type = "Salary Slip", based_on="end_date",
			value_based_on = "rounded_total", time_interval = "Monthly", timeseries = 1,
			filters_json = json.dumps([["Salary Slip", "docstatus", "=", 1]]))
	]

	dashboard_charts.append(
		get_dashboards_chart_doc('Department Wise Salary(Last Month)', "Group By", "Bar",
			document_type = "Salary Slip", group_by_type="Sum", group_by_based_on="department",
			time_interval = "Monthly", aggregate_function_based_on = "rounded_total",
			filters_json = json.dumps([
				["Salary Slip", "docstatus", "=", 1],
				["Salary Slip", "start_date", "Previous","1 month"]
			])
		)
	)

	dashboard_charts.append(
		get_dashboards_chart_doc('Designation Wise Salary(Last Month)', "Group By", "Bar",
			document_type = "Salary Slip", group_by_type="Sum", group_by_based_on="designation",
			time_interval = "Monthly", aggregate_function_based_on = "rounded_total",
			filters_json = json.dumps([
				["Salary Slip", "docstatus", "=", 1],
				["Salary Slip", "start_date", "Previous","1 month"]
			])
		)
	)

	return dashboard_charts

def get_number_cards():
	number_cards = [get_number_cards_doc("Employee Tax Exemption Declaration", "Total Declaration Submitted", filters_json = json.dumps([
				["Employee Tax Exemption Declaration", "docstatus", "=","1"],
				["Employee Tax Exemption Declaration","creation","Previous","1 year"]
			])
		)]

	number_cards.append(get_number_cards_doc("Employee Incentive", "Total Incentive Given(Last month)",
		time_interval = "Monthly", func = "Sum", aggregate_function_based_on = "incentive_amount",
		filters_json = json.dumps([
			["Employee Incentive", "docstatus", "=", 1],
			["Employee Incentive","payroll_date","Previous","1 year"]
		]))
	)

	number_cards.append(get_number_cards_doc("Salary Slip", "Total Outgoing Salary(Last month)",
		time_interval = "Monthly", time_span= "Monthly", func = "Sum", aggregate_function_based_on = "rounded_total",
		filters_json = json.dumps([
			["Salary Slip", "docstatus", "=", 1],
			["Salary Slip", "start_date","Previous","1 month"]
		]))
	)
	number_cards.append(get_number_cards_doc("Salary Structure", "Total Salary Structure",
		filters_json = json.dumps([
			["Salary Structure", "docstatus", "=", 1]
		]))
	)

	return number_cards