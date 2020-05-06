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
				"dashboard_name": "Buying",
				"charts": [
					{ "chart": "Purchase Analytics" },
					{ "chart": "Material Request Purchase Analysis" },
					{ "chart": "Purchase Order Analysis" },
					{ "chart": "Requested Items to Order" },
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
			},
			{
				"doctype": "Dashboard Chart",
				"owner": "Administrator",
				"report_name": "Purchase Analytics",
				"filters_json": json.dumps({
					"tree_type": "Item",
					"doc_type": "Purchase Receipt",
					"value_quantity": "Value",
					"from_date": "2020-03-01",
					"to_date": "2020-07-31",
					"company": company.name,
					"range": "Weekly"
					}),
				"type": "Line",
				'timeseries': 0,
				"chart_type": "Report",
				"chart_name": "Purchase Analytics",
				"custom_options": json.dumps({
					"x_field": "entity",
					"chart_type": "Bar",
					"y_axis_fields": [{"idx": 1, "__islocal": "true", "y_field": "total"}],
					"y_fields": ["total"]
				})
			},
			{
				"doctype": "Dashboard Chart",
				"owner": "Administrator",
				"document_type": "Material Request",
				"filters_json": '[["Material Request","status","not in",["Draft","Cancelled","Stopped",null],false],["Material Request","material_request_type","=","Purchase",false],["Material Request","company","=", "{company}", false]]'.format(company=company.name),
				"is_custom": 0,
				"type": "Donut",
				"timeseries": 0,
				"chart_type": "Group By",
				"group_by_based_on": "status",
				"chart_name": "Material Request Purchase Analysis",
				"group_by_type": "Count",
				"custom_options": json.dumps({"height": 300})

			},
			{
				"doctype": "Dashboard Chart",
				"owner": "Administrator",
				"report_name": "Purchase Order Analysis",
				"filters_json": json.dumps({
					"company": company.name,
					"from_date": "2020-04-04",
					"to_date": "2020-07-04",
					"chart_based_on": "Quantity"
				}),
				"is_custom": 1,
				"type": "Donut",
				"timeseries": 0,
				"chart_type": "Report",
				"chart_name": "Purchase Order Analysis",
				"custom_options": json.dumps({
					"type": "donut",
					"height": 300,
					"axisOptions": {"shortenYAxisNumbers": 1}
				})
			},
			{
				"doctype": "Dashboard Chart",
				"owner": "Administrator",
  				"report_name": "Requested Items to Order",
				"filters_json": json.dumps({
					"company": company.name,
					"from_date": "2020-04-01",
					"to_date": "2020-07-01",
					"group_by_mr": 0
				}),
  				"is_custom": 1,
				"type": "Bar",
				"timeseries": 0,
				"chart_type": "Report",
				"chart_name": "Requested Items to Order",
				"custom_options": json.dumps({
					"type": "bar",
					"barOptions": {"stacked": 1},
					"axisOptions": {"shortenYAxisNumbers": 1}
				})
			}
		]
	}

def get_account(account_type, company):
	accounts = frappe.get_list("Account", filters={"account_type": account_type, "company": company})
	if accounts:
		return accounts[0].name
