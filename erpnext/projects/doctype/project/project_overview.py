# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json
from datetime import date
from functools import cached_property

import frappe
from frappe import _
from frappe.model import get_permitted_fields
from frappe.utils import add_days, date_diff, flt, getdate

from erpnext.projects.doctype.project.project_overview_breakdown import TaskBreakdown
from erpnext.projects.doctype.project.project_overview_progress import PlannedVsCompleted
from erpnext.projects.doctype.project.project_overview_unbilled import get_unbilled_time

CLOSED_STATUSES = ("Completed", "Cancelled")
DUE_SOON_DAYS = 7
ATTENTION_REASONS = ("Overdue", "Blocked", "Unassigned", "Due Soon")
TASK_PRIORITIES = ("Urgent", "High", "Medium", "Low")
ATTENTION_LIMIT = 10
PROJECT_FIELDS = (
	"name",
	"status",
	"actual_time",
	"percent_complete",
	"percent_complete_method",
	"expected_start_date",
	"expected_end_date",
	"company",
	"total_billed_amount",
	"gross_margin",
	"per_gross_margin",
)
MARGIN_FIELDS = ("total_billed_amount", "gross_margin", "per_gross_margin")


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
		"delivery",
		"needs_attention",
		"loose_ends",
		"planned_vs_completed",
		"tasks_by_status",
		"workload",
		"tasks_by_delivery",
		"completed_by_assignee",
		"unbilled",
		"profitability",
	)

	def __init__(self, project: str):
		self.project = frappe.db.get_value("Project", project, PROJECT_FIELDS, as_dict=True)
		# hidden as on the form, where Administrator sees every field
		self.hidden_fields = set()
		if frappe.session.user != "Administrator":
			permitted = set(get_permitted_fields("Project", permission_type="read"))
			self.hidden_fields = {field for field in PROJECT_FIELDS if field not in permitted}
		for field in self.hidden_fields:
			self.project[field] = None
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
		"""Without tasks the user can read, or when every one was cancelled, the tab is a single empty state."""
		return {
			"has_tasks": bool(self.tasks),
			"all_cancelled": bool(self.tasks) and all(task.status == "Cancelled" for task in self.tasks),
			"task_count": len(self.tasks),
		}

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

	def tasks_by_delivery(self) -> dict | None:
		return TaskBreakdown(self).by_delivery() if self.is_closed else None

	def completed_by_assignee(self) -> dict | None:
		return TaskBreakdown(self).by_completer() if self.is_closed else None

	def unbilled(self) -> dict | None:
		return get_unbilled_time(self.project.name)

	def profitability(self) -> dict | None:
		"""Billed against cost, using the gross margin the project stores for its Costing tab, so the two
		always agree; cost is what billing less that margin leaves. With nothing billed there is no
		margin percentage to show. None when the user's permission levels hide those fields."""
		if self.hidden_fields.intersection(MARGIN_FIELDS):
			return None
		billed = flt(self.project.total_billed_amount)
		margin = flt(self.project.gross_margin)
		return {
			"currency": frappe.get_cached_value("Company", self.project.company, "default_currency"),
			"billed": billed,
			"cost": billed - margin,
			"margin": margin,
			"margin_percent": flt(self.project.per_gross_margin, 1) if billed else None,
		}

	def stats(self) -> dict:
		return {
			"open_tasks": self.open_task_stats(),
			"overdue": self.overdue_stats(),
			"hours": self.hours_stats(),
		}

	def delivery(self) -> dict | None:
		"""For a completed or cancelled project, how it ended: when it finished against plan, how far
		it got, and how many tasks were done on time.

		It finished on the latest Completed On of its completed tasks. A task counts as on time when
		it was completed by its Expected End Date; tasks without either date are left out of that count.
		"""
		if not self.is_closed:
			return None

		completed = [task for task in self.tasks if task.status == "Completed"]
		finished_on = max((self.completed_date(task) for task in completed), default=None)
		planned_end = getdate(self.project.expected_end_date) if self.project.expected_end_date else None
		rated = [task for task in completed if self.can_be_late(task)]
		return {
			"status": self.project.status,
			"percent_complete": flt(self.project.percent_complete, 1),
			"finished_on": finished_on,
			"planned_end": planned_end,
			"days_late": date_diff(finished_on, planned_end) if finished_on and planned_end else None,
			"total": len(self.tasks),
			"completed": len(completed),
			"cancelled": sum(1 for task in self.tasks if task.status == "Cancelled"),
			"open": len(self.open_tasks),
			"rated": len(rated),
			"late": sum(1 for task in rated if self.finished_late(task)),
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

	def loose_ends(self) -> dict | None:
		"""For a completed or cancelled project, the tasks it was closed with still open, each under its status.

		Nearly all of them are past their Expected End Date by now, so they are listed under their own
		status rather than as Overdue; the due date shows how late each one is. Sorted by priority, then
		Expected End Date (undated last), then name.
		"""
		if not self.is_closed:
			return None

		tasks = sorted(
			self.open_tasks,
			key=lambda task: (self.priority_rank(task), task.due_date or date.max, task.name),
		)
		return {
			"total": len(tasks),
			"tasks": [
				self.attention_row(self.workflow_status(task), task) for task in tasks[:ATTENTION_LIMIT]
			],
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
		overdue = [task for task in self.open_tasks if self.is_overdue(task)]
		return {
			"count": len(overdue),
			"oldest_days_late": max((self.days_late(task) for task in overdue), default=0),
			"tasks": [task.name for task in overdue],
		}

	def hours_stats(self) -> dict | None:
		"""Hours on submitted Timesheets against the Expected Time of the project's tasks.

		Group tasks are left out of the expected total, as their subtasks carry the estimates. None when
		the user's permission levels hide the hours logged.
		"""
		if "actual_time" in self.hidden_fields:
			return None
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

	def open_status(self, task: frappe._dict) -> str:
		"""An open task's status, with Overdue decided by its Expected End Date as elsewhere on the tab."""
		return "Overdue" if self.is_overdue(task) else self.workflow_status(task)

	def workflow_status(self, task: frappe._dict) -> str:
		"""An open task's status without Overdue, which the daily job sets and may not have reset."""
		return "Open" if task.status == "Overdue" else task.status

	def priority_rank(self, task: frappe._dict) -> int:
		if task.priority in TASK_PRIORITIES:
			return TASK_PRIORITIES.index(task.priority)
		return len(TASK_PRIORITIES)

	def is_overdue(self, task: frappe._dict) -> bool:
		"""Past its Expected End Date, as Task.is_overdue decides; an undated task never is. A task
		Pending Review with its Review Date still ahead isn't either, as set_tasks_as_overdue leaves it be."""
		if not task.due_date or task.due_date >= self.today:
			return False
		awaiting_review = task.status == "Pending Review" and task.review_date
		return not (awaiting_review and getdate(task.review_date) > self.today)

	def is_due_soon(self, task: frappe._dict) -> bool:
		return bool(task.due_date) and self.today <= task.due_date <= self.due_soon_until

	@property
	def is_closed(self) -> bool:
		"""A completed or cancelled project's overview reports how it ended rather than what is open."""
		return self.project.status in CLOSED_STATUSES

	def can_be_late(self, task: frappe._dict) -> bool:
		"""Only a task with both an Expected End Date and a Completed On can be judged on time or late."""
		return bool(task.due_date and task.completed_on)

	def finished_late(self, task: frappe._dict) -> bool:
		return self.can_be_late(task) and self.completed_date(task) > task.due_date

	def completed_date(self, task: frappe._dict) -> date:
		"""Completed On, or the last change for a task completed without one."""
		return getdate(task.completed_on or task.modified)

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
				"review_date",
				"modified",
			],
			limit_page_length=0,
		)
		for task in tasks:
			task.due_date = getdate(task.exp_end_date) if task.exp_end_date else None
			task.assigned_to = json.loads(task._assign or "[]")
			task.is_closed = task.status in CLOSED_STATUSES
		return tasks
