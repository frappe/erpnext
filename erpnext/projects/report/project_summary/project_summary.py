# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = frappe.get_list(
		"Project",
		filters=filters,
		fields=[
			"name",
			"project_name",
			"status",
			"percent_complete",
			"expected_start_date",
			"expected_end_date",
			"project_type",
		],
		order_by="expected_end_date",
	)

	set_task_counts(data)

	chart = get_chart_data(data)
	report_summary = get_report_summary(data)

	return columns, data, None, chart, report_summary


def set_task_counts(projects):
	if not projects:
		return

	task_counts = frappe.get_list(
		"Task",
		filters={"project": ["in", [project.name for project in projects]]},
		fields=["project", "status", {"COUNT": "*", "as": "count"}],
		group_by="project, status",
	)

	for project in projects:
		counts = {row.status: row.count for row in task_counts if row.project == project.name}
		project["total_tasks"] = sum(counts.values())
		project["completed_tasks"] = counts.get("Completed", 0)
		project["overdue_tasks"] = counts.get("Overdue", 0)


def get_columns():
	return [
		{
			"fieldname": "name",
			"label": _("Project"),
			"fieldtype": "Link",
			"options": "Project",
			"width": 200,
		},
		{
			"fieldname": "project_name",
			"label": _("Project Name"),
			"width": 200,
		},
		{
			"fieldname": "project_type",
			"label": _("Type"),
			"fieldtype": "Link",
			"options": "Project Type",
			"width": 120,
		},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 120},
		{"fieldname": "total_tasks", "label": _("Total Tasks"), "fieldtype": "Data", "width": 120},
		{
			"fieldname": "completed_tasks",
			"label": _("Tasks Completed"),
			"fieldtype": "Data",
			"width": 120,
		},
		{"fieldname": "overdue_tasks", "label": _("Tasks Overdue"), "fieldtype": "Data", "width": 120},
		{"fieldname": "percent_complete", "label": _("Completion"), "fieldtype": "Data", "width": 120},
		{
			"fieldname": "expected_start_date",
			"label": _("Start Date"),
			"fieldtype": "Date",
			"width": 120,
		},
		{"fieldname": "expected_end_date", "label": _("End Date"), "fieldtype": "Date", "width": 120},
	]


def get_chart_data(data):
	labels = []
	total = []
	completed = []
	overdue = []

	for project in data:
		labels.append(project.project_name)
		total.append(project.total_tasks)
		completed.append(project.completed_tasks)
		overdue.append(project.overdue_tasks)

	return {
		"data": {
			"labels": labels[:30],
			"datasets": [
				{"name": _("Overdue"), "values": overdue[:30]},
				{"name": _("Completed"), "values": completed[:30]},
				{"name": _("Total Tasks"), "values": total[:30]},
			],
		},
		"type": "bar",
		"colors": ["#fc4f51", "#78d6ff", "#7575ff"],
		"barOptions": {"stacked": True},
	}


def get_report_summary(data):
	if not data:
		return None

	avg_completion = sum(project.percent_complete for project in data) / len(data)
	total = sum([project.total_tasks for project in data])
	total_overdue = sum([project.overdue_tasks for project in data])
	completed = sum([project.completed_tasks for project in data])

	return [
		{
			"value": avg_completion,
			"indicator": "Green" if avg_completion > 50 else "Red",
			"label": _("Average Completion"),
			"datatype": "Percent",
		},
		{
			"value": total,
			"indicator": "Blue",
			"label": _("Total Tasks"),
			"datatype": "Int",
		},
		{
			"value": completed,
			"indicator": "Green",
			"label": _("Completed Tasks"),
			"datatype": "Int",
		},
		{
			"value": total_overdue,
			"indicator": "Green" if total_overdue == 0 else "Red",
			"label": _("Overdue Tasks"),
			"datatype": "Int",
		},
	]
