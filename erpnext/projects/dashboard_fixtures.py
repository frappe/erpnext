# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
import json
from frappe import _

def get_company_for_dashboards():
	company = frappe.defaults.get_defaults().company
	if company:
		return company
	else:
		company_list = frappe.get_list("Company")
		if company_list:
			return company_list[0].name
	return None

def get_data():
	return frappe._dict({
		"dashboards": get_dashboards(),
		"charts": get_charts(),
	})

def get_dashboards():
	return [{
		"doctype": "Dashboard",
		"name": "Project",
		"dashboard_name": "Project",
		"charts": [
			{ "chart": "Project Summary", "width": "Full" }
		]
	}]

def get_charts():
	company = frappe.get_doc("Company", get_company_for_dashboards())

	return [
		{
			'doctype': 'Dashboard Chart',
			'name': 'Project Summary',
			'chart_name': _('Project Summary'),
			'chart_type': 'Report',
			'report_name': 'Project Summary',
			'is_public': 1,
			'is_custom': 1,
			'filters_json': json.dumps({"company": company.name, "status": "Open"}),
			'type': 'Bar',
			'custom_options': '{"type": "bar", "colors": ["#fc4f51", "#78d6ff", "#7575ff"], "axisOptions": { "shortenYAxisNumbers": 1}, "barOptions": { "stacked": 1 }}',
		}
	]