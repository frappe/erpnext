from __future__ import unicode_literals
from frappe import _
import frappe
import json

def get_company_for_dashboards():
	company = frappe.defaults.get_defaults().company
	if company:
		return company
	else:
		company_list = frappe.get_list("Company")
		if company_list:
			return company_list[0].name
	return None

def get_default_dashboards():
	company = frappe.get_doc("Company", get_company_for_dashboards())
	income_account = company.default_income_account or get_account("Income Account", company.name)
	expense_account = company.default_expense_account or get_account("Expense Account", company.name)
	bank_account = company.default_bank_account or get_account("Bank", company.name)

	return {
		"Dashboards": [
			{
				"doctype": "Dashboard",
				"dashboard_name": "Accounts",
				"charts": [
					{ "chart": "Outgoing Bills (Sales Invoice)" },
					{ "chart": "Incoming Bills (Purchase Invoice)" },
					{ "chart": "Bank Balance" },
					{ "chart": "Income" },
					{ "chart": "Expenses" },
					{ "chart": "Patient Appointments" }
				]
			},
			{
				"doctype": "Dashboard",
				"dashboard_name": "Manufacturing",
				"charts": [
					{ "chart": "Work Order Analysis", "width": "Half" },
					{ "chart": "Quality Inspection Analysis", "width": "Half" },
					{ "chart": "Long Time Pending Work Orders", "width": "Half" },
					{ "chart": "Downtime Analysis", "width": "Half" },
					{ "chart": "Production Analysis", "width": "Full" },
					{ "chart": "Job Card Analysis", "width": "Full" }
				]
			}
		],
		"Charts": [
			{
				"doctype": "Dashboard Chart",
				"time_interval": "Quarterly",
				"chart_name": "Income",
				"timespan": "Last Year",
				"color": None,
				"filters_json": json.dumps({"company": company.name, "account": income_account}),
				"source": "Account Balance Timeline",
				"chart_type": "Custom",
				"timeseries": 1,
				"owner": "Administrator",
				"type": "Line",
				"width": "Half"
			},
			{
				"doctype": "Dashboard Chart",
				"time_interval": "Quarterly",
				"chart_name": "Expenses",
				"timespan": "Last Year",
				"color": None,
				"filters_json": json.dumps({"company": company.name, "account": expense_account}),
				"source": "Account Balance Timeline",
				"chart_type": "Custom",
				"timeseries": 1,
				"owner": "Administrator",
				"type": "Line",
				"width": "Half"
			},
			{
				"doctype": "Dashboard Chart",
				"time_interval": "Quarterly",
				"chart_name": "Bank Balance",
				"timespan": "Last Year",
				"color": "#ffb868",
				"filters_json": json.dumps({"company": company.name, "account": bank_account}),
				"source": "Account Balance Timeline",
				"chart_type": "Custom",
				"timeseries": 1,
				"owner": "Administrator",
				"type": "Line",
				"width": "Half"
			},
			{
				"doctype": "Dashboard Chart",
				"time_interval": "Monthly",
				"chart_name": "Incoming Bills (Purchase Invoice)",
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
				"time_interval": "Monthly",
				"chart_name": "Outgoing Bills (Sales Invoice)",
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
				"doctype": "Dashboard Chart",
				"time_interval": "Daily",
				"chart_name": "Patient Appointments",
				"timespan": "Last Month",
				"color": "#77ecca",
				"filters_json": json.dumps({}),
				"chart_type": "Count",
				"timeseries": 1,
				"based_on": "appointment_datetime",
				"owner": "Administrator",
				"document_type": "Patient Appointment",
				"type": "Line",
				"width": "Half"
			}
			{
				"doctype": "Dashboard Chart",
				"time_interval": "Yearly",
				"chart_type": "Report",
				"chart_name": "Work Order Analysis",
				"timespan": "Last Year",
				"report_name": "Work Order Summary",
				"owner": "Administrator",
				"filters_json": json.dumps({"company": company.name}),
				"bar": "Donut",
				"custom_options": json.dumps({
					"axisOptions": {
						"shortenYAxisNumbers": 1
					},
					"height": 300,
					"colors": ["#ff5858", "#ffa00a", "#5e64ff", "#98d85b"]
				}),
			},
			{
				"doctype": "Dashboard Chart",
				"time_interval": "Yearly",
				"chart_type": "Report",
				"chart_name": "Quality Inspection Analysis",
				"timespan": "Last Year",
				"report_name": "Quality Inspection Summary",
				"owner": "Administrator",
				"filters_json": json.dumps({}),
				"bar": "Donut",
				"custom_options": json.dumps({
					"axisOptions": {
						"shortenYAxisNumbers": 1
					},
					"height": 300,
					"colors": ["#ff5858", "#98d85b"]
				}),
			},
			{
				"doctype": "Dashboard Chart",
				"time_interval": "Yearly",
				"chart_type": "Report",
				"chart_name": "Long Time Pending Work Orders",
				"timespan": "Last Year",
				"report_name": "Work Order Summary",
				"filters_json": json.dumps({"company": company.name, "age":180}),
				"owner": "Administrator",
				"bar": "Bar",
				"custom_options": json.dumps({
					"colors": ["#ff5858"],
					"x_field": "name",
					"y_fields": ["age"],
					"y_axis_fields": [{"__islocal": "true", "idx": 1, "y_field": "age"}],
					"chart_type": "Bar"
				}),
			},
			{
				"doctype": "Dashboard Chart",
				"time_interval": "Yearly",
				"chart_type": "Report",
				"chart_name": "Downtime Analysis",
				"timespan": "Last Year",
				"filters_json": json.dumps({}),
				"report_name": "Downtime Analysis",
				"owner": "Administrator",
				"bar": "Bar",
				"custom_options": json.dumps({
					"colors": ["#ff5858"]
				}),
			},
			{
				"doctype": "Dashboard Chart",
				"time_interval": "Yearly",
				"chart_type": "Report",
				"chart_name": "Production Analysis",
				"timespan": "Last Year",
				"report_name": "Production Analytics",
				"owner": "Administrator",
				"filters_json": json.dumps({"company": company.name, "range":"Monthly"}),
				"bar": "Bar",
				"custom_options": json.dumps({
					"colors": ["#7cd6fd", "#ff5858", "#ffa00a", "#98d85b"]
				}),
			},
			{
				"doctype": "Dashboard Chart",
				"time_interval": "Yearly",
				"chart_type": "Report",
				"chart_name": "Job Card Analysis",
				"timespan": "Last Year",
				"report_name": "Job Card Summary",
				"owner": "Administrator",
				"filters_json": json.dumps({"company": company.name, "range":"Monthly"}),
				"bar": "Bar",
				"custom_options": json.dumps({
					"axisOptions": {
						"xAxisMode": "tick"
					},
					"barOptions": {
						"stacked": 1
					},
					"colors": ["#ff5858", "#ffa00a", "#5e64ff", "#98d85b"]
				}),
			},
		]
	}

def get_account(account_type, company):
	accounts = frappe.get_list("Account", filters={"account_type": account_type, "company": company})
	if accounts:
		return accounts[0].name
