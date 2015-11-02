# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe

def execute():
	# convert milestones to tasks
	frappe.reload_doctype("Project")
	frappe.reload_doc("projects", "doctype", "project_task")
	frappe.reload_doctype("Task")
	frappe.reload_doc("projects", "doctype", "task_depends_on")
	frappe.reload_doc("projects", "doctype", "time_log")

	for m in frappe.get_all("Project Milestone", "*"):
		if (m.milestone and m.milestone_date
			and frappe.db.exists("Project", m.parent)):
			subject = (m.milestone[:139] + "…") if (len(m.milestone) > 140) else m.milestone
			description = m.milestone
			task = frappe.get_doc({
				"doctype": "Task",
				"subject": subject,
				"description": description if description!=subject else None,
				"expected_start_date": m.milestone_date,
				"status": "Open" if m.status=="Pending" else "Closed",
				"project": m.parent,
			})
			task.flags.ignore_mandatory = True
			task.insert(ignore_permissions=True)

	# remove project milestone
	frappe.delete_doc("DocType", "Project Milestone")

	# remove calendar events for milestone
	for e in frappe.get_all("Event", ["name"], {"ref_type": "Project"}):
		frappe.delete_doc("Event", e.name)
