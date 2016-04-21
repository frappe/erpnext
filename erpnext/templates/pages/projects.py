# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import json

def get_context(context):
	project_user = frappe.db.get_value("Project User", {"parent": frappe.form_dict.project, "user": frappe.session.user} , "user")
	if not project_user or frappe.session.user == 'Guest': 
		raise frappe.PermissionError
		
	context.no_cache = 1
	context.show_search = True
	context.show_sidebar = True
	project = frappe.get_doc('Project', frappe.form_dict.project)

	project.has_permission('read')
	
	project.tasks = get_tasks(project.name, start=0, item_status='open',
		search=frappe.form_dict.get("q"))

	project.timelogs = get_timelogs(project.name, start=0,
		search=frappe.form_dict.get("q"))


	context.doc = project


def get_tasks(project, start=0, search=None, item_status=None):
	filters = {"project": project}
	if search:
		filters["subject"] = ("like", "%{0}%".format(search))
	if item_status:
		filters["status"] = item_status
	tasks = frappe.get_all("Task", filters=filters,
		fields=["name", "subject", "status", "_seen", "_comments", "modified", "description"],
		limit_start=start, limit_page_length=10)

	for task in tasks:
		task.todo = frappe.get_all('ToDo',filters={'reference_name':task.name, 'reference_type':'Task'},
		fields=["assigned_by", "owner", "modified", "modified_by"])

		if task.todo:
			task.todo=task.todo[0]
			task.todo.user_image = frappe.db.get_value('User', task.todo.owner, 'user_image')

		
		task.comment_count = len(json.loads(task._comments or "[]"))

		task.css_seen = ''
		if task._seen:
			if frappe.session.user in json.loads(task._seen):
				task.css_seen = 'seen'

	return tasks

@frappe.whitelist()
def get_task_html(project, start=0, item_status=None):
	return frappe.render_template("erpnext/templates/includes/projects/project_tasks.html",
		{"doc": {
			"name": project,
			"project_name": project,
			"tasks": get_tasks(project, start, item_status=item_status)}
		}, is_path=True)

def get_timelogs(project, start=0, search=None):
	filters = {"project": project}
	if search:
		filters["title"] = ("like", "%{0}%".format(search))

	timelogs = frappe.get_all('Time Log', filters=filters,
	fields=['name','title','task','activity_type','from_time','to_time','_comments','_seen','status','modified','modified_by'],
	limit_start=start, limit_page_length=10)
	for timelog in timelogs:
		timelog.user_image = frappe.db.get_value('User', timelog.modified_by, 'user_image')
		
		timelog.comment_count = len(json.loads(timelog._comments or "[]"))

		timelog.css_seen = ''
		if timelog._seen:
			if frappe.session.user in json.loads(timelog._seen):
				timelog.css_seen = 'seen'	
	return timelogs

@frappe.whitelist()
def get_timelog_html(project, start=0):
	return frappe.render_template("erpnext/templates/includes/projects/project_timelogs.html",
		{"doc": {"timelogs": get_timelogs(project, start)}}, is_path=True)

