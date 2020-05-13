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
			{ "chart": "Job Application Status", "width": "Half"},
			{ "chart": 'Designation Wise Employee Count', "width": "Half"},
			{ "chart": 'Department Wise Employee Count', "width": "Half"},
			{ "chart": 'Designation Wise Openings', "width": "Half"},
			{ "chart": 'Department Wise Openings', "width": "Half"},
			{ "chart": "Outgoing Salary", "width": "Full"},
			{ "chart": "Attendance Count", "width": "Full"}
		],
		"cards": [
			{"card": "Total Employees"},
			{"card": "New Joinees"},
			{'card': "Employees Left"},
			{'card': "Total Job Openings"},
			{'card': "Total Applicants"},
			{'card': "Short Listed Candidates"},
			{'card': "Rejected Candidates"},
			{'card': "Total Job Offered"},
		]
	}

def get_recruitment_dashboard():
	pass


def get_charts():
	company = erpnext.get_default_company()
	date = frappe.utils.get_datetime()

	month_map = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov","Dec"]


	if not company:
		company = frappe.db.get_value("Company", {"is_group": 0}, "name")

	dashboard_charts = [
		get_dashboards_chart_doc('Gender Diversity Ratio', "Group By", "Donut",document_type = "Employee", group_by_type="Count", group_by_based_on="gender", filters_json = json.dumps([["Employee","status","=","Active"]]), time_interval = "Monthly")
	]

	dashboard_charts.append(
		get_dashboards_chart_doc('Job Application Status', "Group By", "Donut",document_type = "Job Applicant", group_by_type="Count", group_by_based_on="status", filters_json = json.dumps([["Job Applicant","creation","Previous","1 month"]]), time_interval = "Monthly")
	)

	dashboard_charts.append(
		get_dashboards_chart_doc('Outgoing Salary', "Sum", "Line",document_type = "Salary Slip", group_by_type="Count", based_on="end_date", value_based_on = "rounded_total", time_interval = "Monthly", timeseries = 1 , filters_json = json.dumps([["Salary Slip","docstatus","=","1"]]))
	)
	custom_options = '''{"type": "line", "lineOptions": {"dotSize": 6}, "axisOptions": {"shortenYAxisNumbers": 1}, "tooltipOptions": {}}'''
	filters_json = json.dumps({"month": month_map[date.month - 1], "year": str(date.year), "company":company})

	dashboard_charts.append(
		get_dashboards_chart_doc('Attendance Count', "Report", "Line",report_name = "Monthly Attendance Sheet", is_custom =1,group_by_type="Count", filters_json = filters_json, custom_options=custom_options)
	)

	dashboard_charts.append(
		get_dashboards_chart_doc('Department Wise Employee Count', "Group By", "Donut",document_type = "Employee", group_by_type="Count", group_by_based_on="department", filters_json = json.dumps([["Employee","status","=","Active"]]), time_interval = "Monthly")
	)

	dashboard_charts.append(
		get_dashboards_chart_doc('Designation Wise Employee Count', "Group By", "Donut",document_type = "Employee", group_by_type="Count", group_by_based_on="designation", filters_json = json.dumps([["Employee","status","=","Active"]]), time_interval = "Monthly")
	)

	dashboard_charts.append(
		get_dashboards_chart_doc('Designation Wise Openings', "Group By", "Bar",document_type = "Job Opening", group_by_type="Sum", group_by_based_on="designation", time_interval = "Monthly", aggregate_function_based_on = "planned_vacancies")
	)
	dashboard_charts.append(
		get_dashboards_chart_doc('Department Wise Openings', "Group By", "Bar",document_type = "Job Opening", group_by_type="Sum", group_by_based_on="department", time_interval = "Monthly", aggregate_function_based_on = "planned_vacancies")
	)
	return dashboard_charts


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
				["Employee","date_of_joining","Previous","1 year"],
				["Employee","status","=","Active"]
			])
		)
	)

	number_cards.append(
		get_number_cards_doc("Employee", "Employees Left", filters_json = json.dumps([
				["Employee","modified","Previous","1 year"],
				["Employee","status","=","Left"]
			])
		)
	)

	number_cards.append(
		get_number_cards_doc("Job Applicant", "Total Applicants", filters_json = json.dumps([
				["Job Applicant","creation","Previous","1 month"]
			])
		)
	)

	number_cards.append(
		get_number_cards_doc("Job Opening", "Total Job Openings", func = "Sum",aggregate_function_based_on = "planned_vacancies", filters_json = json.dumps([["Job Opening","creation","Previous","1 month"]])
		)
	)
	number_cards.append(
		get_number_cards_doc("Job Applicant", "Short Listed Candidates", filters_json = json.dumps([
				["Job Applicant","status","=","Accepted"],
				["Job Applicant","creation","Previous","1 month"]
			])
		)
	)
	number_cards.append(
		get_number_cards_doc("Job Applicant", "Rejected Candidates", filters_json = json.dumps([
				["Job Applicant","status","=","Rejected"],
				["Job Applicant","creation","Previous","1 month"]
			])
		)
	)
	number_cards.append(
		get_number_cards_doc("Job Offer", "Total Job Offered", filters_json = json.dumps([["Job Offer","creation","Previous","1 month"]])
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
			"aggregate_function_based_on": args.aggregate_function_based_on or None
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
			"aggregate_function_based_on": args.aggregate_function_based_on or None
		}