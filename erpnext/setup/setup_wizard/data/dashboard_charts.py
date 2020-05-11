from __future__ import unicode_literals
from frappe import _
import frappe
import json


def get_default_dashboards():

	return {
		"Dashboards": [
			{
				"doctype": "Dashboard",
				"dashboard_name": "Accounts",
				"charts": [
					{ "chart": "Patient Appointments" }
				]
			}
		],
		"Charts": [
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
		]
	}
