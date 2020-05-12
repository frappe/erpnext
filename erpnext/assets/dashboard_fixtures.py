# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
import json
from frappe.utils import nowdate, add_months

def get_data():
	return frappe._dict({
		"dashboards": get_dashboards(),
		"charts": get_charts(),
		"number_cards": get_number_cards(),
	})

def get_dashboards():
	return [{
		"name": "Asset",
		"dashboard_name": "Asset",
        "charts": [
			{ "chart": "Asset Value Analytics", "width": "Full" },
            { "chart": "Category-wise Asset Value", "width": "Half" },
            { "chart": "Location-wise Asset Value", "width": "Half" },
        ]
    }]

def get_charts():
	company = get_company_for_dashboards()
	fiscal_year = get_fiscal_year()

	return [
		{
			"name": "Asset Value Analytics",
			"chart_name": "Asset Value Analytics",
			"chart_type": "Report",
			"report_name": "Fixed Asset Register",
			"is_custom": 1,
			"group_by_type": "Count",
			"number_of_groups": 0,
			"is_public": 0,
			"timespan": "Last Year",
			"time_interval": "Yearly",
			"timeseries": 0,
			"filters_json": json.dumps({
				"company": company,
				"status": "In Location",
				"filter_based_on": "Fiscal Year",
				"from_fiscal_year": fiscal_year,
				"to_fiscal_year": fiscal_year,
				"period_start_date": add_months(nowdate(), -12),
				"period_end_date": nowdate(),
				"date_based_on": "Purchase Date",
				"group_by": "--Select a group--"
			}),
			"type": "Bar",
			"custom_options": json.dumps({
				"type": "bar",
				"barOptions": { "stacked": 1 },
				"axisOptions": { "shortenYAxisNumbers": 1 },
				"tooltipOptions": {}
			}),
			"doctype": "Dashboard Chart",
			"y_axis": []
		},
		{
			"name": "Category-wise Asset Value",
			"chart_name": "Category-wise Asset Value",
			"chart_type": "Report",
			"report_name": "Fixed Asset Register",
			"x_field": "asset_category",
			"timeseries": 0,
			"filters_json": json.dumps({
				"company": company,
				"status":"In Location",
				"group_by":"Asset Category",
				"is_existing_asset":0
			}),
			"type": "Donut",
			"doctype": "Dashboard Chart",
			"y_axis": [
				{
					"parent": "Category-wise Asset Value",
					"parentfield": "y_axis",
					"parenttype": "Dashboard Chart",
					"y_field": "asset_value",
					"doctype": "Dashboard Chart Field"
				}
			],
			"custom_options": json.dumps({
				"type": "donut",
				"height": 300,
				"axisOptions": {"shortenYAxisNumbers": 1}
			})
		},
		{
			"name": "Location-wise Asset Value",
			"chart_name": "Location-wise Asset Value",
			"chart_type": "Report",
			"report_name": "Fixed Asset Register",
			"x_field": "location",
			"timeseries": 0,
			"filters_json": json.dumps({
				"company": company,
				"status":"In Location",
				"group_by":"Location",
				"is_existing_asset":0
			}),
			"type": "Donut",
			"doctype": "Dashboard Chart",
			"y_axis": [
				{
					"parent": "Location-wise Asset Value",
					"parentfield": "y_axis",
					"parenttype": "Dashboard Chart",
					"y_field": "asset_value",
					"doctype": "Dashboard Chart Field"
				}
			],
			"custom_options": json.dumps({
				"type": "donut",
				"height": 300,
				"axisOptions": {"shortenYAxisNumbers": 1}
			})
		}
	]

def get_number_cards():
	return [
		{
			"name": "Asset Value",
			"label": "Asset Value",
			"function": "Sum",
			"aggregate_function_based_on": "value_after_depreciation",
			"document_type": "Asset",
			"is_public": 1,
			"show_percentage_stats": 1,
			"stats_time_interval": "Monthly",
			"filters_json": "[]",
			"doctype": "Number Card",
		}
	]

def get_company_for_dashboards():
	company = frappe.defaults.get_defaults().company
	if company:
		return company
	else:
		company_list = frappe.get_list("Company")
		if company_list:
			return company_list[0].name
	return None

def get_fiscal_year():
	fiscal_year = frappe.defaults.get_defaults().fiscal_year
	if fiscal_year:
		return fiscal_year
	else:
		fiscal_year_list = frappe.get_list("Fiscal Year")
		if fiscal_year_list:
			return fiscal_year_list[0].name
	return None