// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt"

frappe.module_page["Projects"] = [
	{
		title: frappe._("Top"),
		icon: "icon-copy",
		top: true,
		items: [
			{
				label: frappe._("Task"),
				description: frappe._("Project activity / task."),
				doctype:"Task"
			},
			{
				label: frappe._("Project"),
				description: frappe._("Project master."),
				doctype:"Project"
			},
			{
				label: frappe._("Time Log"),
				description: frappe._("Time Log for tasks."),
				doctype:"Time Log"
			},
		]
	},
	{
		title: frappe._("Documents"),
		icon: "icon-copy",
		items: [
			{
				label: frappe._("Time Log Batch"),
				description: frappe._("Batch Time Logs for billing."),
				doctype:"Time Log Batch"
			},
		]
	},
	{
		title: frappe._("Tools"),
		icon: "icon-wrench",
		items: [
			{
				route: "Gantt/Task",
				label: frappe._("Gantt Chart"),
				"description":frappe._("Gantt chart of all tasks.")
			},
		]
	},
	{
		title: frappe._("Masters"),
		icon: "icon-book",
		items: [
			{
				label: frappe._("Activity Type"),
				description: frappe._("Types of activities for Time Sheets"),
				doctype:"Activity Type"
			},
		]
	},
	{
		title: frappe._("Reports"),
		right: true,
		icon: "icon-list",
		items: [
			{
				"label":frappe._("Daily Time Log Summary"),
				route: "query-report/Daily Time Log Summary",
				doctype: "Time Log"
			},
			{
				"label":frappe._("Project wise Stock Tracking"),
				route: "query-report/Project wise Stock Tracking",
				doctype: "Project"
			},
		]
	}]

pscript['onload_projects-home'] = function(wrapper) {
	frappe.views.moduleview.make(wrapper, "Projects");
}