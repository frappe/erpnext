// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt"

wn.module_page["Projects"] = [
	{
		title: wn._("Top"),
		icon: "icon-copy",
		top: true,
		items: [
			{
				label: wn._("Task"),
				description: wn._("Project activity / task."),
				doctype:"Task"
			},
			{
				label: wn._("Project"),
				description: wn._("Project master."),
				doctype:"Project"
			},
			{
				label: wn._("Time Log"),
				description: wn._("Time Log for tasks."),
				doctype:"Time Log"
			},
		]
	},
	{
		title: wn._("Documents"),
		icon: "icon-copy",
		items: [
			{
				label: wn._("Time Log Batch"),
				description: wn._("Batch Time Logs for billing."),
				doctype:"Time Log Batch"
			},
		]
	},
	{
		title: wn._("Tools"),
		icon: "icon-wrench",
		items: [
			{
				route: "Gantt/Task",
				label: wn._("Gantt Chart"),
				"description":wn._("Gantt chart of all tasks.")
			},
		]
	},
	{
		title: wn._("Masters"),
		icon: "icon-book",
		items: [
			{
				label: wn._("Activity Type"),
				description: wn._("Types of activities for Time Sheets"),
				doctype:"Activity Type"
			},
		]
	},
	{
		title: wn._("Reports"),
		right: true,
		icon: "icon-list",
		items: [
			{
				"label":wn._("Daily Time Log Summary"),
				route: "query-report/Daily Time Log Summary",
				doctype: "Time Log"
			},
			{
				"label":wn._("Project wise Stock Tracking"),
				route: "query-report/Project wise Stock Tracking",
				doctype: "Project"
			},
		]
	}]

pscript['onload_projects-home'] = function(wrapper) {
	wn.views.moduleview.make(wrapper, "Projects");
}