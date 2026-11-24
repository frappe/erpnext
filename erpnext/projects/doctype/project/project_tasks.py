# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.model import get_permitted_fields, optional_fields

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
		fields=["name", *fields],
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

	Owner-only rules, user permissions and shared tasks make this differ between tasks, so it is
	checked per task, except when no role or share lets the user write any task.
	"""
	can_write_any = frappe.has_permission("Task", "write")
	for row in rows:
		row.can_write = bool(can_write_any and frappe.has_permission("Task", "write", doc=row.name))
