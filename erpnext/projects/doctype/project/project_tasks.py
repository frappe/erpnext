# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.model import default_fields, get_permitted_fields, optional_fields
from frappe.permissions import get_role_permissions

from erpnext.projects.doctype.project.project_overview import check_access

# The most tasks the Tasks tab loads. It groups, sorts and searches them in the browser, so it
# loads them all at once rather than a page at a time.
TASK_LIMIT = 2000

TASK_FIELDS = (
	"subject",
	"status",
	"priority",
	"exp_start_date",
	"exp_end_date",
	"progress",
	"_assign",
	"parent_task",
	"is_group",
	"is_milestone",
	"actual_time",
	"lft",
	"rgt",
	"creation",
	"modified",
)
# what the tab changes on a task in place; the rest is changed in the task's dialog
EDITABLE_FIELDS = ("status", "priority")


@frappe.whitelist(methods=["GET"])
def get_project_task_list(project: str) -> dict:
	"""Return the tasks of a project the user can read, for the Project form's Tasks tab.

	Rows are the tasks the Task list would show the user: role permissions, "only if owner",
	user permissions and shared tasks all apply. Fields the user may not read are left out and
	listed in neither `fields` nor `editable`, so the tab hides their columns. `_assign` comes back
	parsed, as `assigned_to`.
	"""
	check_access(project)

	# the query engine lets anyone who can read a task read `_assign`, though no permlevel lists it
	readable = {*get_permitted_fields("Task", permission_type="read"), *optional_fields}
	fields = [field for field in TASK_FIELDS if field in readable]
	rows = frappe.qb.get_query(
		"Task",
		# the owner decides write access where a role grants it only to the task's owner
		fields=["name", "owner", *fields],
		filters={"project": project},
		order_by="creation asc",
		limit=TASK_LIMIT + 1,
		ignore_permissions=False,
	).run(as_dict=True)
	truncated = len(rows) > TASK_LIMIT
	rows = rows[:TASK_LIMIT]

	set_top_parents(rows)
	set_write_access(rows)
	for row in rows:
		row.assigned_to = frappe.parse_json(row.pop("_assign", None) or "[]")
		row.pop("lft", None)
		row.pop("rgt", None)
		row.pop("owner", None)

	meta = frappe.get_meta("Task")
	# a save resets only fields above permlevel 0 that the user's roles can't write, so permlevel 0
	# is writable wherever the task is (a task shared for writing included)
	write_levels = {0, *meta.get_permlevel_access("write")}
	return {
		"project": project,
		"tasks": rows,
		"truncated": truncated,
		"fields": [
			"assigned_to" if field == "_assign" else field for field in fields if field not in ("lft", "rgt")
		],
		"editable": [
			field
			for field in EDITABLE_FIELDS
			if field in readable and meta.get_field(field).permlevel in write_levels
		],
		"can_create": bool(frappe.has_permission("Task", "create")),
		# Select fields sort by their options, which Customize Form can change
		"options": {
			field: (meta.get_field(field).options or "").split("\n")
			for field in ("status", "priority")
			if field in readable
		},
	}


def set_top_parents(rows: list[dict]) -> None:
	"""Set `top_parent` on each row: the top-level parent task it sits under, however deep.

	Only parents in `rows` count, so the tab never names a task the user can't read: a task whose
	top-level parent is hidden from the user gets none, and shows under "No parent task".
	"""
	tops = [
		row
		for row in rows
		if row.get("is_group") and not row.get("parent_task") and row.get("lft") is not None
	]
	for row in rows:
		row.top_parent = None
		if not row.get("parent_task") or row.get("lft") is None:
			continue
		for top in tops:
			if top.lft < row.lft and row.rgt <= top.rgt:
				row.top_parent = top.name
				break


def set_write_access(rows: list[dict]) -> None:
	"""Set `can_write` on each row, so the tab offers edits only where a save would go through.

	Checking each task loads it, one query a task, and the tab loads on every visit and edit. So
	the answer is worked out once for all rows, unless something can make it differ between tasks
	in a way only the task itself shows: a permission hook, or a User Permission on what Task links
	to. Without those, a task is writable when a role lets the user write any task, or only their
	own and they made it, or it is shared with them for writing.
	"""
	user = frappe.session.user
	if user == "Administrator":
		for row in rows:
			row.can_write = True
		return

	# a role lets the user write every task, or only the ones they made; shares come separately
	every_task = frappe.has_permission("Task", "write", ignore_share_permissions=True)
	own_tasks = "write" in get_role_permissions(frappe.get_meta("Task"), user=user).get("if_owner", {})

	if write_access_differs_per_task(user):
		# Frappe's answer without a task leaves out "only if owner", so it can't stand in for the
		# owner's own tasks; it is skipped only for a user who can write no task by any route
		if not (every_task or own_tasks or frappe.share.get_shared("Task", user, ["write"], limit=1)):
			for row in rows:
				row.can_write = False
			return
		for row in rows:
			row.can_write = bool(frappe.has_permission("Task", "write", doc=row.name))
		return

	shared = set() if every_task else set(frappe.share.get_shared("Task", user, ["write"]))
	for row in rows:
		row.can_write = bool(
			every_task
			or (own_tasks and (row.get("owner") or "").lower() == user.lower())
			or row.name in shared
		)


# ERPNext's own hook for every doctype; it denies only where a doctype links to a company-restricted
# master, which Task doesn't
INHERITED_PERMISSION = (
	"erpnext.stock.doctype.company_restriction.company_restriction.has_inherited_permission"
)


def write_access_differs_per_task(user: str) -> bool:
	"""Whether a task's write access can depend on more than its owner and its shares."""
	from frappe.core.doctype.user_permission.user_permission import get_user_permissions

	from erpnext.stock.doctype.company_restriction.company_restriction import get_inherited_master_links

	hooks = frappe.get_hooks("has_permission")
	for method in [*hooks.get("Task", []), *hooks.get("*", [])]:
		if method != INHERITED_PERMISSION or get_inherited_master_links("Task"):
			return True

	restricted = set(get_user_permissions(user))
	if not restricted:
		return False
	# User Permissions apply through Task's links and its child tables' links
	linked = {"Task"}
	meta = frappe.get_meta("Task")
	for each in [meta, *(frappe.get_meta(df.options) for df in meta.get_table_fields())]:
		linked.update(df.options for df in each.get_link_fields() if not df.ignore_user_permissions)
	return bool(restricted & linked)


# the task tree's fields, which the system keeps
SYSTEM_FIELDS = {"lft", "rgt", "old_parent"}


@frappe.whitelist(methods=["POST"])
def create_task(task: dict | str, assign_to: list | str | None = None) -> dict:
	"""Create a task from the task dialog and assign it, in one go; return the saved task.

	The dialog is Task's quick entry everywhere, so the project is optional, and `task` also holds
	what the page that opened it filled in, such as the Issue the task is made from. Any Task field
	is taken except the ones the system keeps. The task is inserted with the user's own
	permissions and Task's usual checks, which also leave fields at a permlevel the user can't
	write as they were, as desk's quick entry does. The assignments are added in the same request,
	so a refused assignment leaves no task behind.
	"""
	values = frappe.parse_json(task) or {}
	assign_to = frappe.parse_json(assign_to) or []

	fields = set(frappe.get_meta("Task").get_valid_columns()) - set(default_fields) - SYSTEM_FIELDS
	doc = frappe.get_doc(
		{
			"doctype": "Task",
			**{
				field: value for field, value in values.items() if field in fields and value not in (None, "")
			},
		}
	)
	doc.insert()

	if assign_to:
		from frappe.desk.form.assign_to import _add

		# checked as the Assign dialog checks them: `add` checks assignees only when it is the
		# endpoint called, not from Python, so a Website User or a disabled user would get through
		_add(
			{"doctype": "Task", "name": doc.name, "assign_to": assign_to, "description": doc.subject},
			ignore_permissions=False,
			validate_assignees=True,
		)
	return doc.copy_with_fieldlevel_read_permissions().as_dict()
