import json

import frappe


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
					{"chart": "Outgoing Bills (Sales Invoice)"},
					{"chart": "Incoming Bills (Purchase Invoice)"},
					{"chart": "Bank Balance"},
					{"chart": "Income"},
					{"chart": "Expenses"},
					{"chart": "Patient Appointments"},
				],
			},
			{
				"doctype": "Dashboard",
				"dashboard_name": "Project",
				"charts": [{"chart": "Project Summary", "width": "Full"}],
			},
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
				"width": "Half",
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
				"width": "Half",
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
				"width": "Half",
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
				"width": "Half",
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
				"width": "Half",
			},
			{
				"doctype": "Dashboard Chart",
				"name": "Project Summary",
				"chart_name": "Project Summary",
				"chart_type": "Report",
				"report_name": "Project Summary",
				"is_public": 1,
				"filters_json": json.dumps({"company": company.name, "status": "Open"}),
				"type": "Bar",
				"custom_options": '{"type": "bar", "colors": ["#fc4f51", "#78d6ff", "#7575ff"], "axisOptions": { "shortenYAxisNumbers": 1}, "barOptions": { "stacked": 1 }}',
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
				"width": "Half",
			},
		],
	}


def get_account(account_type, company):
	accounts = frappe.get_list("Account", filters={"account_type": account_type, "company": company})
	if accounts:
		return accounts[0].name
