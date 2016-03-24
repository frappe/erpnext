# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import json

def get_context(context):
	context.no_cache = 1

	project = frappe.get_doc('Project', frappe.form_dict.project)

	project.has_permission('read')

	context.issues = frappe.get_all('Issue', filters={'project': project.project_name},
	fields=['subject', 'opening_date', 'resolution_date', 'status', 'name', 'resolution_details','modified','modified_by'])

	project.tasks = get_tasks(project.name, start=0, search=frappe.form_dict.get("q"))

	project.timelogs = get_timelogs(project.name, start=0, search=frappe.form_dict.get("q"))

	project.issues = get_issues(project.name, start=0, search=frappe.form_dict.get("q"))

	project.timelines = get_timeline(project.project_name, start=0)



	context.doc = project


def get_timeline(project, start=10):
	'''Get timeline from project, tasks, issues'''
	issues_condition = ''
	project_issues = get_issues(project)

	if project_issues:
		issue_names = '({0})'.format(", ".join(["'{0}'".format(i.name) for i in project_issues]))
		issues_condition = """or (reference_doctype='Issue' and reference_name IN {issue_names})""".format(issue_names=issue_names)


	timelines = frappe.db.sql("""
		select
			sender_full_name,
			subject, communication_date, comment_type, name, creation, modified_by, reference_doctype, reference_name,
			_liked_by, comment_type, _comments
		from
			tabCommunication
		where
			(reference_doctype='Project' and reference_name=%s)
			or (timeline_doctype='Project' and timeline_name=%s)
			{issues_condition}
		order by
			modified DESC limit {start}, {limit}""".format(
			issues_condition=issues_condition, start=start, limit=10),
			(project, project), as_dict=True);
	for timeline in timelines:
 		timeline.user_image = frappe.db.get_value('User', timeline.modified_by, 'user_image')
	return timelines

@frappe.whitelist()
def get_timelines_html(project, start=0):
	return frappe.render_template("erpnext/templates/includes/projects/timeline.html",
		{"doc": {"timelines": get_timeline(project, start)}}, is_path=True)

def get_issue_list(project):
	return [issue.name for issue in get_issues(project)]

def get_tasks(project, start=0, search=None, item_status=None):
	filters = {"project": project}
	if search:
		filters["subject"] = ("like", "%{0}%".format(search))
	if item_status:
		filters = {"status": item_status}
	tasks = frappe.get_all("Task", filters=filters,
		fields=["name", "subject", "status", "exp_start_date", "exp_end_date", "priority"],
		limit_start=start, limit_page_length=10)

	for task in tasks:
		print task._comments
		task.todo = frappe.get_all('ToDo',filters={'reference_name':task.name, 'reference_type':'Task'},
		fields=["assigned_by", "owner", "modified", "modified_by"])
		if task.todo:
			task.todo=task.todo[0]
			task.todo.user_image = frappe.db.get_value('User', task.todo.owner, 'user_image')
		if task._comments:
			task.comment_count = len(json.loads(task._comments or "[]"))
	return tasks

@frappe.whitelist()
def get_tasks_html(project, start=0, item_status=None):
	return frappe.render_template("erpnext/templates/includes/projects/project_tasks.html",
		{"doc": {"tasks": get_tasks(project, start, item_status=item_status)}}, is_path=True)


def get_issues(project, start=0, search=None, item_status=None):
	filters = {"project": project}
	if search:
		filters["subject"] = ("like", "%{0}%".format(search))
	if item_status:
		filters = {"status": item_status}
	issues = frappe.get_all("Issue", filters=filters,
		fields=["name", "subject", "status", "opening_date", "resolution_date", "resolution_details"],
		order_by='modified desc',
		limit_start=start, limit_page_length=10)

	for issue in issues:
		issue.todo = frappe.get_all('ToDo',filters={'reference_name':issue.name, 'reference_type':'Issue'},
		fields=["assigned_by", "owner", "modified", "modified_by"])
		if issue.todo:
			issue.todo=issue.todo[0]
			issue.todo.user_image = frappe.db.get_value('User', issue.todo.owner, 'user_image')

	return issues

@frappe.whitelist()
def get_issues_html(project, start=0, item_status=None):
	return frappe.render_template("erpnext/templates/includes/projects/project_issues.html",
		{"doc": {"issues": get_issues(project, start, item_status=item_status)}}, is_path=True)

def get_timelogs(project, start=0, search=None):
	filters = {"project": project}
	if search:
		filters["title"] = ("like", "%{0}%".format(search))

	timelogs = frappe.get_all('Time Log', filters=filters,
	fields=['name','title','task','activity_type','from_time','to_time','hours','status','modified','modified_by'],
	limit_start=start, limit_page_length=10)
	for timelog in timelogs:
		timelog.user_image = frappe.db.get_value('User', timelog.modified_by, 'user_image')
	return timelogs

@frappe.whitelist()
def get_timelogs_html(project, start=0):
	return frappe.render_template("erpnext/templates/includes/projects/project_timelogs.html",
		{"doc": {"timelogs": get_timelogs(project, start)}}, is_path=True)

@frappe.whitelist()
def set_task_status(project, item_name):
	task = frappe.get_doc("Task", item_name)
	task.status = 'Closed'
	task.save(ignore_permissions=True)

@frappe.whitelist()
def set_issue_status(project, item_name):
	issue = frappe.get_doc("Issue", item_name)
	issue.status = 'Closed'
	issue.save(ignore_permissions=True)

