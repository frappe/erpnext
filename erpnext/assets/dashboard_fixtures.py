# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
import json


def get_data():
	return frappe._dict({
		"dashboards": get_dashboards(),
		"charts": get_charts()
	})

def get_dashboards():
	return [{
		"name": "Asset",
		"dashboard_name": "Asset",
        "charts": [
            { "chart": "Category-wise Asset Value" },
            { "chart": "Location-wise Asset Value" },
        ]
    }]

def get_charts():
	return [
		{
			"name": "Category-wise Asset Value",
			"chart_name": "Category-wise Asset Value",
			"chart_type": "Report",
			"report_name": "Fixed Asset Report",
			"is_custom": 1,
			"x_field": "asset_category",
			"timeseries": 0,
			"filters_json": json.dumps("""{"status":"In Location","group_by":"Asset Category","is_existing_asset":0}"""),
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
			"report_name": "Location-wise Asset Value",
			"is_custom": 1,
			"x_field": "location",
			"timeseries": 0,
			"filters_json": json.dumps("""{"status":"In Location","group_by":"Location","is_existing_asset":0}"""),
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
		}]
