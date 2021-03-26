# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import date_diff, nowdate

def execute(filters=None):
	columns, data = [], []
	data = get_data(filters)
	columns = get_columns()
	charts = get_chart_data(data)
	return columns, data, None, charts

def get_data(filters):
	conditions = get_conditions(filters)
	tasks = frappe.get_all("Task", conditions, ["name", "subject", "exp_start_date", "exp_end_date", "status", "priority", "completed_on", "progress"], order_by="creation")
	for task in tasks:
		if task.exp_end_date:
			if task.completed_on:
				task.delay = date_diff(task.completed_on, task.exp_end_date)
			else:
				task.delay = date_diff(nowdate(), task.exp_end_date)
	return tasks

def get_conditions(filters):
	conditions = frappe._dict()
	keys = ["priority", "status"]
	for key in keys:
		if filters.get(key):
			conditions[key] = filters.get(key)
	if filters.get("from_date"):
		conditions.exp_end_date = [">=", filters.get("from_date")]
	if filters.get("to_date"):
		conditions.exp_start_date = ["<=", filters.get("to_date")]
	return conditions

def get_chart_data(data):
	on_track = []
	delay = []

	for entry in data:
		if entry.get("delay") > 0:
			delay.append(entry.get("delay"))
		else:
			on_track.append(entry.get("delay"))
	charts = {
		'data': {
			'labels': ["On Track", "Delayed"],
			'datasets': [
				{
					'name': 'Delayed',
					'values': [len(on_track), len(delay)]
				}
			]
		},
		'type': 'percentage',
		"colors": ["#84D5BA", "#CB4B5F"]
	}
	return charts

def get_columns():
	columns = [
		{
			"fieldname": "name",
			"fieldtype": "Link",
			"label": "Task",
			"options": "Task",
			"width": 150
		},
		{
			"fieldname": "subject",
			"fieldtype": "Data",
			"label": "Subject",
			"width": 200
		},
		{
			"fieldname": "status",
			"fieldtype": "Data",
			"label": "Status",
			"width": 100
		},
		{
			"fieldname": "priority",
			"fieldtype": "Data",
			"label": "Priority",
			"width": 100
		},
		{
			"fieldname": "progress",
			"fieldtype": "Data",
			"label": "Progress (%)",
			"width": 100
		},
		{
			"fieldname": "exp_start_date",
			"fieldtype": "Date",
			"label": "Expected Start Date",
			"width": 150
		},
		{
			"fieldname": "exp_end_date",
			"fieldtype": "Date",
			"label": "Expected End Date",
			"width": 150
		},
		{
			"fieldname": "completed_on",
			"fieldtype": "Date",
			"label": "Actual End Date",
			"width": 130
		},
		{
			"fieldname": "delay",
			"fieldtype": "Data",
			"label": "Delay",
			"width": 70
		}
	]
	return columns
