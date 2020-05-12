# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
import json


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

def get_dashboards():
	return [{
		"name": "Buying",
		"dashboard_name": "Buying",
		"charts": [
			{ "chart": "Purchase Analytics", "width": "Full"},
			{ "chart": "Material Request Purchase Analysis", "width": "Half"},
			{ "chart": "Purchase Order Analysis", "width": "Half"},
			{ "chart": "Requested Items to Order", "width": "Full"}
		]
	}]

def get_charts():
	return [
		{
			"name": "Purchase Analytics",
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
			"x_field": "entity",
			"type": "Bar",
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
			"name": "Material Request Purchase Analysis",
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
			"name": "Purchase Order Analysis",
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
			"name": "Requested Items to Order",
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

def get_number_cards():
	return [{}]