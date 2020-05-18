# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
import json


def get_data():
	return frappe._dict({
		"dashboards": get_dashboards(),
		"charts": get_charts(),
	})

def get_dashboards():
	return [{
		"name": "Healthcare",
		"dashboard_name": "Healthcare",
		"charts": [
			{ "chart": "Patient Appointments" }
		]
	}]

def get_charts():
	return [
			{
				"doctype": "Dashboard Chart",
				"time_interval": "Daily",
				"name": "Patient Appointments",
				"chart_name": "Patient Appointments",
				"timespan": "Last Month",
				"filters_json": json.dumps({}),
				"chart_type": "Count",
				"timeseries": 1,
				"based_on": "appointment_datetime",
				"owner": "Administrator",
				"document_type": "Patient Appointment",
				"type": "Line",
				"width": "Half"
			}
		]
