from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Projects"),
			"icon": "icon-star",
			"items": [
				{
					"type": "doctype",
					"name": "Project",
					"description": _("Project master."),
				},
				{
					"type": "doctype",
					"name": "Task",
					"description": _("Project activity / task."),
				},
				{
					"type": "report",
					"route": "Gantt/Task",
					"doctype": "Task",
					"name": "Gantt Chart",
					"description": _("Gantt chart of all tasks.")
				},
			]
		},
		{
			"label": _("Time Tracking"),
			"items": [
				{
					"type": "doctype",
					"name": "Time Log",
					"description": _("Time Log for tasks."),
				},
				{
					"type": "doctype",
					"name": "Time Log Batch",
					"description": _("Batch Time Logs for billing."),
				},
				{
					"type": "doctype",
					"name": "Activity Type",
					"description": _("Types of activities for Time Sheets"),
				},
				{
					"type": "doctype",
					"name": "Activity Cost",
					"description": _("Cost of various activities"),
				},
			]
		},
		{
			"label": _("Reports"),
			"icon": "icon-list",
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Daily Time Log Summary",
					"doctype": "Time Log"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Project wise Stock Tracking",
					"doctype": "Project"
				},
			]
		},
		{
			"label": _("Help"),
			"icon": "icon-facetime-video",
			"items": [
				{
					"type": "help",
					"label": _("Managing Projects"),
					"youtube_id": "egxIGwtoKI4"
				},
			]
		},
	]
