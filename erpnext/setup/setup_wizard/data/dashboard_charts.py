from __future__ import unicode_literals
from frappe import _
import frappe
import json

def get_default_dashboards():
	company = frappe.get_doc("Company", frappe.defaults.get_defaults().company)
	income_account = company.default_income_account or get_account("Income Account", company.name)
	expense_account = company.default_expense_account or get_account("Expense Account", company.name)
	bank_account = company.default_bank_account or get_account("Bank", company.name)

	return {
		"Dashboards": [
			{
				"doctype": "Dashboard",
				"dashboard_name": "Accounts",
				"charts": [
					{ "chart": "Billing Value" },
					{ "chart": "Purchase Value" },
					{ "chart": "Bank Balance" },
					{ "chart": "Income" },
					{ "chart": "Expense" }
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
				"value_based_on": "",
				"filters_json": json.dumps({"company": company.name, "account": income_account}),
				"source": "Account Balance Timeline",
				"chart_type": "Custom",
				"timeseries": 1,
				"based_on": "",
				"owner": "Administrator",
				"document_type": "",
				"type": "Line",
				"width": "Half"
			},
			{
				"doctype": "Dashboard Chart",
				"time_interval": "Quarterly",
				"chart_name": "Expense",
				"timespan": "Last Year",
				"color": None,
				"value_based_on": "",
				"filters_json": json.dumps({"company": company.name, "account": expense_account}),
				"source": "Account Balance Timeline",
				"chart_type": "Custom",
				"timeseries": 1,
				"based_on": "",
				"owner": "Administrator",
				"document_type": "",
				"type": "Line",
				"width": "Half"
			},
			{
				"doctype": "Dashboard Chart",
				"time_interval": "Quarterly",
				"chart_name": "Bank Balance",
				"timespan": "Last Year",
				"color": "#ffb868",
				"value_based_on": "",
				"filters_json": json.dumps({"company": company.name, "account": bank_account}),
				"source": "Account Balance Timeline",
				"chart_type": "Custom",
				"timeseries": 1,
				"based_on": "",
				"owner": "Administrator",
				"document_type": "",
				"type": "Line",
				"width": "Half"
			},
			{
				"doctype": "Dashboard Chart",
				"time_interval": "Monthly",
				"chart_name": "Purchase Value",
				"timespan": "Last Year",
				"color": "#a83333",
				"value_based_on": "base_grand_total",
				"filters_json": json.dumps({}),
				"source": "",
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
				"chart_name": "Billing Value",
				"timespan": "Last Year",
				"color": "#7b933d",
				"value_based_on": "base_grand_total",
				"filters_json": json.dumps({}),
				"source": "",
				"chart_type": "Sum",
				"timeseries": 1,
				"based_on": "posting_date",
				"owner": "Administrator",
				"document_type": "Sales Invoice",
				"type": "Bar",
				"width": "Half"
			}
		]
	}

def get_account(account_type, company):
	accounts = frappe.get_list("Account", filters={"account_type": account_type, "company": company})
	if accounts:
		return accounts[0].name