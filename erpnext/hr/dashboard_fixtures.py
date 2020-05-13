# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
import erpnext
import json

def get_data():
	return frappe._dict({
		"dashboards": get_dashboards(),
		"charts": get_charts(),
		"number_cards": get_number_cards(),
	})

def get_dashboards():
	dashboards = []
	dashboards.append(get_human_resource_dashboard())
	return dashboards

def get_human_resource_dashboard():
	return {
		"name": "Human Resource",
		"dashboard_name": "Human Resource",
		"is_default": 1,
		"charts": [
			{ "chart": "Gender Diversity Ratio", "width": "Half"},
			{ "chart": "Employee Count", "width": "Half"},
			{ "chart": "Outgoing Salary", "width": "Full"},
			{ "chart": "Attendance Count", "width": "Full"}
		],
		"cards": [
			{"card": "Total Employees"},
			{"card": "New Joinees"},
			{'card': "Job Applicants"},
			{'card': "Employees Left"}
		]
	}

def get_recruitment_dashboard():
	pass
	# return {
	# 	"name": "Human Resource",
	# 	"dashboard_name": "Human Resource",
	# 	"is_default": 1,
	# 	"charts": [
	# 	],
	# 	"cards": [
	# 	]
	# }


def get_charts():
	company = erpnext.get_default_company()

	if not company:
		company = frappe.db.get_value("Company", {"is_group": 0}, "name")

	dashboard_charts = [
		get_dashboards_chart_doc('Gender Diversity Ratio', "Group By", "Donut",document_type = "Employee", group_by_type="Count", group_by_based_on="gender", filters_json = json.dumps([["Employee","status","=","Active"]]), time_interval = "Monthly")
	]

	dashboard_charts.append(
		get_dashboards_chart_doc('Outgoing salary', "Sum", "Line",document_type = "Salary Slip", group_by_type="Count", based_on="end_date", value_based_on = "rounded_total", time_interval = "Monthly", timeseries = 1 , filters_json = json.dumps([["Salary Slip","docstatus","=","1"]]))
	)

	custom_options = '''{"type": "bar", "axisOptions": {"shortenYAxisNumbers": 1}, "tooltipOptions": {}, "barOptions":{"stacked": 1}}'''
	filters_json = json.dumps({"month":"May","year":"2020","company":company})

	dashboard_charts.append(
		get_dashboards_chart_doc('Attendance Count', "Report", "Bar",report_name = "Monthly Attendance Sheet", is_custom =1,group_by_type="Count", timeseries = 1 , filters_json = filters_json, custom_options=custom_options)
	)

	custom_options = """{"type": "donut", "axisOptions": {"shortenYAxisNumbers": 1}}"""
	filters_json = json.dumps({"company":company ,"parameter":"Department"})

	dashboard_charts.append(
		get_dashboards_chart_doc('Employee Count', "Report", "Donut",report_name = "Employee Analytics", is_custom =1, group_by_type="Count", timeseries = 1 , filters_json = filters_json, custom_options=custom_options)
	)




def get_number_cards():
	number_cards = []

	number_cards = [
		get_number_cards_doc("Employee", "Total Employees", filters_json = json.dumps([
				["Employee","status","=","Active"]
			])
		)
	]
	number_cards.append(
		get_number_cards_doc("Employee", "New Joinees", filters_json = json.dumps([
				["Employee","date_of_joining","Previous","6 months"],
				["Employee","status","=","Active"]
			]),
			stats_time_interval = "Daily")
		)
	number_cards.append(
		get_number_cards_doc("Employee", "Employees Left", filters_json = json.dumps([
				["Employee","status","=","Left"]
			])
		)
	)
	number_cards.append(
		get_number_cards_doc("Job Applicant", "Job Applicants", filters_json = json.dumps([
				["Job Applicant","status","!=","Rejected"]
			])
		)
	)

	return number_cards


def get_number_cards_doc(document_type, label, **args):
	args = frappe._dict(args)

	return {
			"doctype": "Number Card",
			"document_type": document_type,
			"function": args.func or "Count",
			"is_public": args.is_public or 1,
			"label": label,
			"name": args.name or label,
			"show_percentage_stats": args.show_percentage_stats or 1,
			"stats_time_interval": args.stats_time_interval or 'Monthly',
			"filters_json": args.filters_json or '[]',
		}

def get_dashboards_chart_doc(name, chart_type, graph_type, **args):

	args = frappe._dict(args)

	return {
			"name": name,
			"chart_name": args.chart_name or name,
			"chart_type": chart_type,
			"document_type": args.document_type or None,
			"report_name": args.report_name or None,
			"is_custom": args.is_custom or 0,
			"group_by_type": args.group_by_type or None,
			"group_by_based_on": args.group_by_based_on or None,
			"based_on": args.based_on or None,
			"value_based_on": args.value_based_on or None,
			"number_of_groups": args.number_of_groups or 0,
			"is_public": args.is_public or 1,
			"timespan": args.timespan or "Last Year",
			"time_interval": args.time_interval or "Yearly",
			"timeseries": args.timeseries or 0,
			"filters_json": args.filters_json or '[]',
			"type": graph_type,
			"custom_options": args.custom_options or '',
			"doctype": "Dashboard Chart",
		}