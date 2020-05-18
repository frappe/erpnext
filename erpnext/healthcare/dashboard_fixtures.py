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
			{ "chart": "Patient Appointments", "width": "Full"},
			{ "chart": "In-Patient Status", "width": "Half"},
			{ "chart": "Clinical Procedures Status", "width": "Half"},
			{ "chart": "Symptoms", "width": "Half"},
			{ "chart": "Diagnoses", "width": "Half"},
			{ "chart": "Department wise Patient Appointments", "width": "Full"},
			{ "chart": "Lab Tests", "width": "Full"},
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
			},
			{
				"doctype": "Dashboard Chart",
				"name": "Department wise Patient Appointments",
				"chart_name": "Department wise Patient Appointments",
				"chart_type": "Group By",
				"document_type": "Patient Appointment",
				"group_by_type": "Count",
				"group_by_based_on": "department",
				'is_public': 1,
				"owner": "Administrator",
				"type": "Bar",
				"width": "Full",
				"color": "#5F62F6"
			},
			{
				"doctype": "Dashboard Chart",
				"name": "Lab Tests",
				"chart_name": "Lab Tests",
				"chart_type": "Group By",
				"document_type": "Lab Test",
				"group_by_type": "Count",
				"group_by_based_on": "template",
				'is_public': 1,
				"owner": "Administrator",
				"type": "Bar",
				"width": "Full",
				"color": "#8548EB"
			},
			{
				"doctype": "Dashboard Chart",
				"name": "In-Patient Status",
				"chart_name": "In-Patient Status",
				"chart_type": "Group By",
				"document_type": "Inpatient Record",
				"group_by_type": "Count",
				"group_by_based_on": "status",
				'is_public': 1,
				"owner": "Administrator",
				"type": "Bar",
				"width": "Half",
			},
			{
				"doctype": "Dashboard Chart",
				"name": "Clinical Procedures Status",
				"chart_name": "Clinical Procedure Status",
				"chart_type": "Group By",
				"document_type": "Clinical Procedure",
				"group_by_type": "Count",
				"group_by_based_on": "status",
				'is_public': 1,
				"owner": "Administrator",
				"type": "Pie",
				"width": "Half",
			},
			{
				"doctype": "Dashboard Chart",
				"name": "Symptoms",
				"chart_name": "Symptoms",
				"chart_type": "Group By",
				"document_type": "Patient Encounter Symptom",
				"group_by_type": "Count",
				"group_by_based_on": "complaint",
				'is_public': 1,
				"owner": "Administrator",
				"type": "Percentage",
				"width": "Half",
			},
			{
				"doctype": "Dashboard Chart",
				"name": "Diagnoses",
				"chart_name": "Diagnoses",
				"chart_type": "Group By",
				"document_type": "Patient Encounter Diagnosis",
				"group_by_type": "Count",
				"group_by_based_on": "diagnosis",
				'is_public': 1,
				"owner": "Administrator",
				"type": "Percentage",
				"width": "Half",
			}
		]
