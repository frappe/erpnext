# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json

import frappe
from frappe import _, throw
from frappe.desk.form.assign_to import clear, close_all_assignments
from frappe.model.mapper import get_mapped_doc
from frappe.utils import add_days, cstr, date_diff, flt, get_link_to_form, getdate, today
from frappe.utils.data import format_date
from frappe.utils.nestedset import NestedSet


class CircularReferenceError(frappe.ValidationError):
	pass


class ParentIsGroupError(frappe.ValidationError):
	pass


class Task(NestedSet):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.projects.doctype.task_depends_on.task_depends_on import TaskDependsOn

		act_end_date: DF.Date | None
		act_start_date: DF.Date | None
		actual_time: DF.Float
		closing_date: DF.Date | None
		color: DF.Color | None
		company: DF.Link | None
		completed_by: DF.Link | None
		completed_on: DF.Date | None
		department: DF.Link | None
		depends_on: DF.Table[TaskDependsOn]
		depends_on_tasks: DF.Code | None
		description: DF.TextEditor | None
		duration: DF.Int
		exp_end_date: DF.Date | None
		exp_start_date: DF.Date | None
		expected_time: DF.Float
		is_group: DF.Check
		is_milestone: DF.Check
		is_template: DF.Check
		issue: DF.Link | None
		lft: DF.Int
		old_parent: DF.Data | None
		parent_task: DF.Link | None
		priority: DF.Literal["Low", "Medium", "High", "Urgent"]
		progress: DF.Percent
		project: DF.Link | None
		review_date: DF.Date | None
		rgt: DF.Int
		start: DF.Int
		status: DF.Literal[
			"Open", "Working", "Pending Review", "Overdue", "Template", "Completed", "Cancelled"
		]
		subject: DF.Data
		task_weight: DF.Float
		template_task: DF.Data | None
		total_billing_amount: DF.Currency
		total_costing_amount: DF.Currency
		type: DF.Link | None
	# end: auto-generated types

	nsm_parent_field = "parent_task"

	def get_customer_details(self):
		cust = frappe.db.sql("select customer_name from `tabCustomer` where name=%s", self.customer)
		if cust:
			ret = {"customer_name": cust and cust[0][0] or ""}
			return ret

	def validate(self):
		self.validate_dates()
		self.validate_progress()
		self.validate_status()
		self.clear_completion_on_reopen()
		self.update_depends_on()
		self.validate_dependencies_for_template_task()
		self.validate_completed_on()
		self.validate_parent_is_group()
		self.validate_parent_not_completed()
		self.validate_web_form_project_permission()

	def validate_dates(self):
		self.validate_from_to_dates("exp_start_date", "exp_end_date")
		self.validate_from_to_dates("act_start_date", "act_end_date")
		self.validate_parent_expected_end_date()
		self.validate_parent_project_dates()

	def validate_parent_expected_end_date(self):
		if not self.parent_task or not self.exp_end_date:
			return

		parent_exp_end_date = frappe.db.get_value("Task", self.parent_task, "exp_end_date")
		if not parent_exp_end_date:
			return

		if getdate(self.exp_end_date) > getdate(parent_exp_end_date):
			self.report_date_conflict(
				_(
					"Expected End Date should be less than or equal to parent task's Expected End Date {0}."
				).format(format_date(parent_exp_end_date)),
				"exp_end_date",
				"parent_task",
			)

	def validate_parent_project_dates(self):
		if not self.project or frappe.flags.in_test:
			return

		project_start_date, project_end_date = frappe.db.get_value(
			"Project", self.project, ["expected_start_date", "expected_end_date"]
		)

		for fieldname in ("exp_start_date", "exp_end_date"):
			task_date = self.get(fieldname)
			if not task_date:
				continue
			task_date = getdate(task_date)

			if project_end_date and date_diff(getdate(project_end_date), task_date) < 0:
				self.report_date_conflict(
					_("{0}'s {1} cannot be after {2}'s Expected End Date.").format(
						get_link_to_form("Task", self.name),
						_(self.meta.get_label(fieldname)),
						get_link_to_form("Project", self.project),
					),
					fieldname,
					"project",
				)

			if project_start_date and date_diff(task_date, getdate(project_start_date)) < 0:
				self.report_date_conflict(
					_("{0}'s {1} cannot be before {2}'s Expected Start Date.").format(
						get_link_to_form("Task", self.name),
						_(self.meta.get_label(fieldname)),
						get_link_to_form("Project", self.project),
					),
					fieldname,
					"project",
				)

	def report_date_conflict(self, message: str, *fieldnames: str):
		"""Refuse a date conflict this save causes; warn when a reschedule causes it."""
		if not self.flags.rescheduled:
			if self.is_new() or any(self.has_value_changed(fieldname) for fieldname in fieldnames):
				frappe.throw(message, frappe.exceptions.InvalidDates)
			return

		frappe.msgprint(
			_("{0} was moved after the task it depends on. {1}").format(
				get_link_to_form("Task", self.name), message
			),
			title=_("Schedule Conflict"),
			indicator="orange",
		)

	def validate_status(self):
		if self.is_template and self.status != "Template":
			self.status = "Template"
		if self.status == "Overdue" and not (self.exp_end_date and getdate(self.exp_end_date) < getdate()):
			self.status = "Working" if self.actual_time else "Open"
		if self.status != self.get_db_value("status") and self.status == "Completed":
			for d in self.depends_on:
				if frappe.db.get_value("Task", d.task, "status") not in ("Completed", "Cancelled"):
					frappe.throw(
						_(
							"Cannot complete task {0} as its dependant task {1} are not completed / cancelled."
						).format(frappe.bold(self.name), frappe.bold(d.task))
					)

			close_all_assignments(self.doctype, self.name)

	def validate_progress(self):
		if not 0 <= flt(self.progress) <= 100:
			frappe.throw(_("Progress % for a task must be between 0 and 100."))

		if self.status == "Completed":
			self.progress = 100

	def clear_completion_on_reopen(self):
		previous_status = (self.get_doc_before_save() or frappe._dict()).get("status")
		if previous_status != "Completed" or self.status in ("Completed", "Cancelled"):
			return

		self.completed_on = None
		self.completed_by = None
		if not self.has_value_changed("progress"):
			self.progress = 0

	def validate_dependencies_for_template_task(self):
		if self.is_template:
			self.validate_parent_template_task()
			self.validate_depends_on_tasks()

	def validate_parent_template_task(self):
		if self.parent_task:
			if not frappe.db.get_value("Task", self.parent_task, "is_template"):
				frappe.throw(
					_("Parent Task {0} is not a Template Task").format(
						get_link_to_form("Task", self.parent_task)
					)
				)

	def validate_depends_on_tasks(self):
		if self.depends_on:
			for task in self.depends_on:
				if not frappe.db.get_value("Task", task.task, "is_template"):
					frappe.throw(
						_("Dependent Task {0} is not a Template Task").format(
							get_link_to_form("Task", task.task)
						)
					)

	def validate_completed_on(self):
		if self.completed_on and getdate(self.completed_on) > getdate():
			frappe.throw(_("Completed On cannot be greater than Today"))

	def validate_parent_is_group(self):
		if self.parent_task:
			if not frappe.db.get_value("Task", self.parent_task, "is_group"):
				frappe.throw(
					_("Parent Task {0} must be a Group Task").format(
						get_link_to_form("Task", self.parent_task)
					),
					ParentIsGroupError,
				)

	def validate_parent_not_completed(self):
		if not self.parent_task or self.status in ("Completed", "Cancelled"):
			return

		if (
			self.has_value_changed("parent_task")
			and frappe.db.get_value("Task", self.parent_task, "status") == "Completed"
		):
			frappe.throw(
				_("Cannot add an open task under completed Parent Task {0}.").format(
					get_link_to_form("Task", self.parent_task)
				)
			)

	def update_depends_on(self):
		depends_on_tasks = ""
		for d in self.depends_on:
			if d.task and d.task not in depends_on_tasks:
				depends_on_tasks += d.task + ","
		self.depends_on_tasks = depends_on_tasks

	def update_nsm_model(self):
		frappe.utils.nestedset.update_nsm(self)

	def on_update(self):
		self.update_nsm_model()
		self.check_recursion()
		self.remove_from_previous_parent_depends_on()
		self.reschedule_dependent_tasks()
		self.update_project()
		self.update_previous_project()
		self.unassign_todo()
		self.populate_depends_on()

	def unassign_todo(self):
		if self.status == "Completed":
			close_all_assignments(self.doctype, self.name)
		if self.status == "Cancelled":
			clear(self.doctype, self.name)

	def update_time_and_costing(self):
		tl = frappe.db.sql(
			"""select min(from_time) as start_date, max(to_time) as end_date,
			sum(billing_amount) as total_billing_amount, sum(costing_amount) as total_costing_amount,
			sum(hours) as time from `tabTimesheet Detail` where task = %s and docstatus=1""",
			self.name,
			as_dict=1,
		)[0]
		if self.status == "Open":
			self.status = "Working"
		self.total_costing_amount = tl.total_costing_amount
		self.total_billing_amount = tl.total_billing_amount
		self.actual_time = tl.time
		self.act_start_date = tl.start_date
		self.act_end_date = tl.end_date

	def update_project(self):
		if self.project and not self.flags.from_project:
			frappe.get_cached_doc("Project", self.project).update_project()

	def update_previous_project(self):
		previous_project = (self.get_doc_before_save() or frappe._dict()).get("project")
		if previous_project and previous_project != self.project:
			frappe.get_cached_doc("Project", previous_project).update_project()

	def check_recursion(self):
		if self.flags.ignore_recursion_check:
			return
		check_list = [["task", "parent"], ["parent", "task"]]
		for d in check_list:
			task_list, count = [self.name], 0
			while len(task_list) > count:
				tasks = frappe.db.sql(
					" select {} from `tabTask Depends On` where {} = {} ".format(d[0], d[1], "%s"),
					cstr(task_list[count]),
				)
				count = count + 1
				for b in tasks:
					if b[0] == self.name:
						frappe.throw(_("Circular Reference Error"), CircularReferenceError)
					if b[0]:
						task_list.append(b[0])

				if count == 15:
					break

	def reschedule_dependent_tasks(self):
		end_date = self.exp_end_date or self.act_end_date
		if not end_date or self.flags.ignore_reschedule:
			return

		dependent_parents = frappe.get_all(
			"Task Depends On",
			filters={"task": self.name, "parent": ["!=", self.parent_task or ""]},
			pluck="parent",
		)
		if not dependent_parents:
			return

		for task_name in frappe.get_all(
			"Task",
			filters={"project": self.project, "name": ["in", dependent_parents]},
			pluck="name",
		):
			task = frappe.get_doc("Task", task_name)
			if (
				task.exp_start_date
				and task.exp_end_date
				and task.exp_start_date < getdate(end_date)
				and task.status in ("Open", "Working", "Overdue")
			):
				task_duration = date_diff(task.exp_end_date, task.exp_start_date)
				task.exp_start_date = add_days(end_date, 1)
				task.exp_end_date = add_days(task.exp_start_date, task_duration)
				task.flags.ignore_recursion_check = True
				task.flags.rescheduled = True
				task.save()

	def has_webform_permission(self):
		project_user = frappe.db.get_value(
			"Project User", {"parent": self.project, "user": frappe.session.user}, "user"
		)
		if project_user:
			return True

	def validate_web_form_project_permission(self):
		project_unchanged = not self.is_new() and self.project == self.get_db_value("project")

		if (
			not frappe.flags.in_web_form
			or not self.project
			or project_unchanged
			or frappe.has_permission("Project", "write", doc=self.project)
			or self.has_webform_permission()
		):
			return

		frappe.throw(
			_("You are not permitted to create a Task for Project {0}").format(self.project),
			frappe.PermissionError,
		)

	def populate_depends_on(self):
		if self.parent_task:
			parent = frappe.get_doc("Task", self.parent_task)
			if self.name not in [row.task for row in parent.depends_on]:
				parent.append(
					"depends_on", {"doctype": "Task Depends On", "task": self.name, "subject": self.subject}
				)
				parent.save()

	def remove_from_previous_parent_depends_on(self):
		previous_parent = (self.get_doc_before_save() or frappe._dict()).get("parent_task")
		if previous_parent != self.parent_task:
			self.remove_from_parent_depends_on(previous_parent)

	def remove_from_parent_depends_on(self, parent_task: str | None):
		if not parent_task:
			return

		parent = frappe.get_doc("Task", parent_task)
		rows = [row for row in parent.depends_on if row.task != self.name]
		if len(rows) != len(parent.depends_on):
			parent.set("depends_on", rows)
			parent.save(ignore_permissions=True)

	def on_trash(self):
		if check_if_child_exists(self.name):
			throw(_("Child Task exists for this Task. You can not delete this Task."))

		self.remove_from_parent_depends_on(self.parent_task)
		self.update_nsm_model()

	def after_delete(self):
		self.update_project()

	def update_status(self):
		if self.status not in ("Cancelled", "Completed") and self.exp_end_date:
			from datetime import datetime

			if self.exp_end_date < datetime.now().date():
				self.db_set("status", "Overdue", update_modified=False)
				self.update_project()


@frappe.whitelist()
def check_if_child_exists(name):
	child_tasks = frappe.get_all("Task", filters={"parent_task": name})
	child_tasks = [get_link_to_form("Task", task.name) for task in child_tasks]
	return child_tasks


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_project(doctype, txt, searchfield, start, page_len, filters):
	from erpnext.controllers.queries import get_match_cond

	meta = frappe.get_meta(doctype)
	searchfields = meta.get_search_fields()
	search_columns = ", " + ", ".join(searchfields) if searchfields else ""
	search_cond = " or " + " or ".join(field + " like %(txt)s" for field in searchfields)

	return frappe.db.sql(
		f""" select name {search_columns} from `tabProject`
		where %(key)s like %(txt)s
			%(mcond)s
			{search_cond}
		order by name
		limit %(page_len)s offset %(start)s""",
		{
			"key": searchfield,
			"txt": "%" + txt + "%",
			"mcond": get_match_cond(doctype),
			"start": start,
			"page_len": page_len,
		},
	)


@frappe.whitelist()
def set_multiple_status(names, status):
	names = json.loads(names)
	for name in names:
		task = frappe.get_doc("Task", name)
		task.status = status
		task.save()


def set_tasks_as_overdue():
	tasks = frappe.get_all(
		"Task",
		filters={"status": ["not in", ["Cancelled", "Completed", "Template"]]},
		fields=["name", "status", "review_date"],
	)
	for task in tasks:
		if task.status == "Pending Review":
			if getdate(task.review_date) > getdate(today()):
				continue
		frappe.get_doc("Task", task.name).update_status()


@frappe.whitelist()
def make_timesheet(source_name, target_doc=None, ignore_permissions=False):
	def set_missing_values(source, target):
		target.parent_project = source.project
		target.append(
			"time_logs",
			{
				"hours": source.actual_time,
				"completed": source.status == "Completed",
				"project": source.project,
				"task": source.name,
			},
		)

	doclist = get_mapped_doc(
		"Task",
		source_name,
		{"Task": {"doctype": "Timesheet"}},
		target_doc,
		postprocess=set_missing_values,
		ignore_permissions=ignore_permissions,
	)

	return doclist


@frappe.whitelist()
def get_children(doctype, parent, task=None, project=None, is_root=False):
	filters = [["docstatus", "<", "2"]]

	if task:
		filters.append(["parent_task", "=", task])
	elif parent and not is_root:
		# via expand child
		filters.append(["parent_task", "=", parent])
	else:
		filters.append(['ifnull(`parent_task`, "")', "=", ""])

	if project:
		filters.append(["project", "=", project])

	tasks = frappe.get_list(
		doctype,
		fields=["name as value", "subject as title", "is_group as expandable"],
		filters=filters,
		order_by="name",
	)

	# return tasks
	return tasks


@frappe.whitelist()
def add_node():
	from frappe.desk.treeview import make_tree_args

	args = frappe.form_dict
	args.update({"name_field": "subject"})
	args = make_tree_args(**args)

	if args.parent_task == "All Tasks" or args.parent_task == args.project:
		args.parent_task = None

	frappe.get_doc(args).insert()


@frappe.whitelist()
def add_multiple_tasks(data, parent, project=None):
	data = json.loads(data)
	is_root = parent in ("All Tasks", project)
	new_doc = {
		"doctype": "Task",
		"parent_task": None if is_root else parent,
		"project": project if is_root else frappe.db.get_value("Task", parent, "project"),
	}

	for d in data:
		if not d.get("subject"):
			continue
		new_doc["subject"] = d.get("subject")
		new_task = frappe.get_doc(new_doc)
		new_task.insert()


def on_doctype_update():
	frappe.db.add_index("Task", ["lft", "rgt"])
