# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json
from datetime import date
from functools import cached_property

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, flt, getdate

from erpnext.projects.doctype.project.project_overview_breakdown import TaskBreakdown
from erpnext.projects.doctype.project.project_overview_progress import PlannedVsCompleted
from erpnext.projects.doctype.project.project_overview_unbilled import get_unbilled_time

CLOSED_STATUSES = ("Completed", "Cancelled")
DUE_SOON_DAYS = 7
# most urgent first; a task is listed once, under the first reason that applies
ATTENTION_REASONS = ("Overdue", "Blocked", "Unassigned", "Due Soon")
# highest first; a task without a priority comes after Low
TASK_PRIORITIES = ("Urgent", "High", "Medium", "Low")
ATTENTION_LIMIT = 10


@frappe.whitelist()
def get_project_overview(project: str) -> dict:
	"""Return the data behind the Project form's Overview tab."""
	check_access(project)
	return ProjectOverview(project).build()


def check_access(project: str) -> None:
	if not frappe.has_permission("Project", "read", doc=project):
		frappe.throw(_("Not permitted"), frappe.PermissionError)


class ProjectOverview:
	"""Builds the sections of one project's Overview tab from a single read of its tasks.

	Each section is built on its own: one that fails comes back as None and is flagged in
	`errors`, so the tab can still render the others.
	"""

	SECTIONS = (
		"summary",
		"milestone",
		"stats",
		"needs_attention",
		"planned_vs_completed",
		"tasks_by_status",
		"workload",
		"unbilled",
	)

	def __init__(self, project: str):
		self.project = frappe.db.get_value(
			"Project",
			project,
			[
				"name",
				"status",
				"actual_time",
				"percent_complete_method",
				"expected_start_date",
				"expected_end_date",
			],
			as_dict=True,
		)
		self.today = getdate()
		self.due_soon_until = add_days(self.today, DUE_SOON_DAYS)

	def build(self) -> dict:
		payload = {"project": self.project.name, "as_of": str(self.today), "errors": {}}
		for section in self.SECTIONS:
			try:
				payload[section] = getattr(self, section)()
			except Exception:
				payload[section] = None
				payload["errors"][section] = 1
				frappe.log_error(title="Project Overview: " + section)
		return payload

	def summary(self) -> dict:
		"""Without tasks the user can read, the tab is a single empty state."""
		return {"has_tasks": bool(self.tasks)}

	def milestone(self) -> dict:
		"""The open milestone due first (undated ones last), and whether every milestone is done."""
		milestones = [task for task in self.tasks if task.is_milestone]
		upcoming = sorted(
			(task for task in milestones if task.status not in CLOSED_STATUSES),
			key=lambda task: (task.due_date is None, task.due_date or self.today),
		)
		return {
			"next": self.milestone_details(upcoming[0]) if upcoming else None,
			"all_met": bool(milestones) and not upcoming,
		}

	def planned_vs_completed(self) -> dict:
		return PlannedVsCompleted(self.project, self.tasks, self.today).build()

	def tasks_by_status(self) -> dict:
		return TaskBreakdown(self).by_status()

	def workload(self) -> dict:
		return TaskBreakdown(self).by_assignee()

	def unbilled(self) -> dict | None:
		return get_unbilled_time(self.project.name)

	def stats(self) -> dict:
		return {
			"open_tasks": self.open_task_stats(),
			"overdue": self.overdue_stats(),
			"hours": self.hours_stats(),
		}

	def needs_attention(self) -> dict:
		"""Open tasks that need a look, each under its most pressing reason.

		Sorted by reason, then priority, then Expected End Date (undated last), then name so ties
		keep a stable order.
		"""
		reasons = {task.name: self.attention_reason(task) for task in self.open_tasks}
		flagged = sorted(
			((reasons[task.name], task) for task in self.open_tasks if reasons[task.name]),
			key=lambda item: (
				ATTENTION_REASONS.index(item[0]),
				self.priority_rank(item[1]),
				item[1].due_date or date.max,
				item[1].name,
			),
		)
		return {
			"total": len(flagged),
			"tasks": [self.attention_row(reason, task) for reason, task in flagged[:ATTENTION_LIMIT]],
			"due_soon_days": DUE_SOON_DAYS,
		}

	def milestone_details(self, task: frappe._dict) -> dict:
		return {
			"task": task.name,
			"subject": task.subject,
			"due_date": task.due_date,
			"days_left": date_diff(task.due_date, self.today) if task.due_date else None,
		}

	def open_task_stats(self) -> dict:
		return {
			"count": len(self.open_tasks),
			"due_soon": sum(1 for task in self.open_tasks if self.is_due_soon(task)),
			"due_soon_days": DUE_SOON_DAYS,
		}

	def overdue_stats(self) -> dict:
		days_late = [self.days_late(task) for task in self.open_tasks if self.is_overdue(task)]
		return {"count": len(days_late), "oldest_days_late": max(days_late, default=0)}

	def hours_stats(self) -> dict:
		"""Hours on submitted Timesheets against the Expected Time of the project's tasks.

		Group tasks are left out of the expected total, as their subtasks carry the estimates.
		"""
		expected = sum(
			flt(task.expected_time) for task in self.tasks if task.status != "Cancelled" and not task.is_group
		)
		return {"logged": flt(self.project.actual_time), "expected": expected}

	def attention_reason(self, task: frappe._dict) -> str | None:
		"""Group tasks are not flagged as unassigned, as the work sits with their subtasks.

		Lacking an Expected End Date is not a reason on its own; an undated task is listed only when
		it is blocked or unassigned.
		"""
		if self.is_overdue(task):
			return "Overdue"
		if task.name in self.blocked_tasks:
			return "Blocked"
		if not task.assigned_to and not task.is_group:
			return "Unassigned"
		if self.is_due_soon(task):
			return "Due Soon"
		return None

	def attention_row(self, reason: str, task: frappe._dict) -> dict:
		return {
			"task": task.name,
			"subject": task.subject,
			"reason": reason,
			"assigned_to": task.assigned_to,
			"due_date": task.due_date,
			"days_late": self.days_late(task) if self.is_overdue(task) else 0,
		}

	def priority_rank(self, task: frappe._dict) -> int:
		if task.priority in TASK_PRIORITIES:
			return TASK_PRIORITIES.index(task.priority)
		return len(TASK_PRIORITIES)

	def is_overdue(self, task: frappe._dict) -> bool:
		"""Past its Expected End Date, as Task.is_overdue decides; an undated task never is."""
		return bool(task.due_date) and task.due_date < self.today

	def is_due_soon(self, task: frappe._dict) -> bool:
		return bool(task.due_date) and self.today <= task.due_date <= self.due_soon_until

	def days_late(self, task: frappe._dict) -> int:
		return date_diff(self.today, task.due_date)

	@cached_property
	def blocked_tasks(self) -> set[str]:
		"""Open tasks that depend on a task which is neither completed nor cancelled.

		A group task's own subtasks are left out: ERPNext adds them to its Depends On by itself, so
		counting them would mark every group task with open work as blocked.
		"""
		if not self.open_tasks:
			return set()

		dependencies = frappe.get_all(
			"Task Depends On",
			filters={"parenttype": "Task", "parent": ["in", [task.name for task in self.open_tasks]]},
			fields=["parent", "task"],
		)
		if not dependencies:
			return set()

		unfinished = {
			task.name: task.parent_task
			for task in frappe.get_all(
				"Task",
				filters={
					"name": ["in", list({row.task for row in dependencies})],
					"status": ["not in", CLOSED_STATUSES],
				},
				fields=["name", "parent_task"],
			)
		}
		return {
			row.parent
			for row in dependencies
			if row.task in unfinished and unfinished[row.task] != row.parent
		}

	@cached_property
	def open_tasks(self) -> list[frappe._dict]:
		return [task for task in self.tasks if not task.is_closed]

	@cached_property
	def tasks(self) -> list[frappe._dict]:
		"""Every task of the project the user can read, with its Expected End as a date."""
		tasks = frappe.get_list(
			"Task",
			filters={"project": self.project.name, "is_template": 0, "status": ["!=", "Template"]},
			fields=[
				"name",
				"subject",
				"status",
				"priority",
				"exp_end_date",
				"expected_time",
				"is_group",
				"is_milestone",
				"_assign",
				"task_weight",
				"progress",
				"exp_start_date",
				"completed_on",
				"modified",
			],
			limit_page_length=0,
		)
		for task in tasks:
			task.due_date = getdate(task.exp_end_date) if task.exp_end_date else None
			task.assigned_to = json.loads(task._assign or "[]")
			task.is_closed = task.status in CLOSED_STATUSES
		return tasks
