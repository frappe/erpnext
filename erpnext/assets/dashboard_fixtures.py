# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json

import frappe
from frappe import _
from frappe.utils import get_date_str, nowdate

from erpnext.accounts.dashboard_fixtures import _get_fiscal_year
from erpnext.buying.dashboard_fixtures import get_company_for_dashboards


def get_data():
	fiscal_year = _get_fiscal_year(nowdate())

	if not fiscal_year:
		return frappe._dict()

	year_start_date = get_date_str(fiscal_year.get("year_start_date"))
	year_end_date = get_date_str(fiscal_year.get("year_end_date"))

	return frappe._dict(
		{
			"dashboards": get_dashboards(),
			"charts": get_charts(fiscal_year, year_start_date, year_end_date),
			"number_cards": get_number_cards(fiscal_year, year_start_date, year_end_date),
		}
	)


def get_dashboards():
	return [
		{
			"name": "Asset",
			"dashboard_name": "Asset",
			"charts": [
				{"chart": "Asset Value Analytics", "width": "Full"},
				{"chart": "Category-wise Asset Value", "width": "Half"},
				{"chart": "Location-wise Asset Value", "width": "Half"},
			],
			"cards": [
				{"card": "Total Assets"},
				{"card": "New Assets (This Year)"},
				{"card": "Asset Value"},
			],
		}
	]


def get_charts(fiscal_year, year_start_date, year_end_date):
	company = get_company_for_dashboards()
	return [
		{
			"name": "Asset Value Analytics",
			"chart_name": _("Asset Value Analytics"),
			"chart_type": "Report",
			"report_name": "Fixed Asset Register",
			"is_custom": 1,
			"group_by_type": "Count",
			"number_of_groups": 0,
			"is_public": 0,
			"timespan": "Last Year",
			"time_interval": "Yearly",
			"timeseries": 0,
			"filters_json": json.dumps(
				{
					"company": company,
					"status": "In Location",
					"filter_based_on": "Fiscal Year",
					"from_fiscal_year": fiscal_year.get("name"),
					"to_fiscal_year": fiscal_year.get("name"),
					"period_start_date": year_start_date,
					"period_end_date": year_end_date,
					"date_based_on": "Purchase Date",
					"group_by": "--Select a group--",
				}
			),
			"type": "Bar",
			"custom_options": json.dumps(
				{
					"type": "bar",
					"barOptions": {"stacked": 1},
					"axisOptions": {"shortenYAxisNumbers": 1},
					"tooltipOptions": {},
				}
			),
			"doctype": "Dashboard Chart",
			"y_axis": [],
		},
		{
			"name": "Category-wise Asset Value",
			"chart_name": _("Category-wise Asset Value"),
			"chart_type": "Report",
			"report_name": "Fixed Asset Register",
			"x_field": "asset_category",
			"timeseries": 0,
			"filters_json": json.dumps(
				{
					"company": company,
					"status": "In Location",
					"group_by": "Asset Category",
					"is_existing_asset": 0,
				}
			),
			"type": "Donut",
			"doctype": "Dashboard Chart",
			"y_axis": [
				{
					"parent": "Category-wise Asset Value",
					"parentfield": "y_axis",
					"parenttype": "Dashboard Chart",
					"y_field": "asset_value",
					"doctype": "Dashboard Chart Field",
				}
			],
			"custom_options": json.dumps(
				{"type": "donut", "height": 300, "axisOptions": {"shortenYAxisNumbers": 1}}
			),
		},
		{
			"name": "Location-wise Asset Value",
			"chart_name": "Location-wise Asset Value",
			"chart_type": "Report",
			"report_name": "Fixed Asset Register",
			"x_field": "location",
			"timeseries": 0,
			"filters_json": json.dumps(
				{"company": company, "status": "In Location", "group_by": "Location", "is_existing_asset": 0}
			),
			"type": "Donut",
			"doctype": "Dashboard Chart",
			"y_axis": [
				{
					"parent": "Location-wise Asset Value",
					"parentfield": "y_axis",
					"parenttype": "Dashboard Chart",
					"y_field": "asset_value",
					"doctype": "Dashboard Chart Field",
				}
			],
			"custom_options": json.dumps(
				{"type": "donut", "height": 300, "axisOptions": {"shortenYAxisNumbers": 1}}
			),
		},
	]


def get_number_cards(fiscal_year, year_start_date, year_end_date):
	return [
		{
			"name": "Total Assets",
			"label": _("Total Assets"),
			"function": "Count",
			"document_type": "Asset",
			"is_public": 1,
			"show_percentage_stats": 1,
			"stats_time_interval": "Monthly",
			"filters_json": "[]",
			"doctype": "Number Card",
		},
		{
			"name": "New Assets (This Year)",
			"label": _("New Assets (This Year)"),
			"function": "Count",
			"document_type": "Asset",
			"is_public": 1,
			"show_percentage_stats": 1,
			"stats_time_interval": "Monthly",
			"filters_json": json.dumps([["Asset", "creation", "between", [year_start_date, year_end_date]]]),
			"doctype": "Number Card",
		},
		{
			"name": "Asset Value",
			"label": _("Asset Value"),
			"function": "Sum",
			"aggregate_function_based_on": "value_after_depreciation",
			"document_type": "Asset",
			"is_public": 1,
			"show_percentage_stats": 1,
			"stats_time_interval": "Monthly",
			"filters_json": "[]",
			"doctype": "Number Card",
		},
	]
