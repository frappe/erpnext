# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from functools import cached_property
from typing import TYPE_CHECKING

import frappe

if TYPE_CHECKING:
	from erpnext.projects.doctype.project.project_overview import ProjectOverview

TASK_STATUSES = ("Open", "Working", "Pending Review", "Overdue", "Completed", "Cancelled")
DELIVERY_OUTCOMES = ("On Time", "Late", "No Due Date", "Still Open", "Cancelled")


class TaskBreakdown:
	"""Tasks by Status and Open Tasks by Assignee, for a project's Overview tab.

	Reads the tasks the overview has already loaded, and decides Overdue the way its
	stat cards do.
	"""

	def __init__(self, overview: "ProjectOverview"):
		self.overview = overview

	def by_status(self) -> dict:
		"""Tasks per status; an open task past its Expected End Date counts as Overdue, whatever its saved
		status. Each status lists its tasks, so a slice opens exactly the tasks it counts. Statuses added
		through Customize Form follow the standard ones, alphabetically."""
		tasks = {}
		for task in self.overview.tasks:
			tasks.setdefault(self.status(task), []).append(task.name)
		custom = sorted(status for status in tasks if status not in TASK_STATUSES)
		return {
			"statuses": [
				{"status": status, "count": len(tasks[status]), "tasks": tasks[status]}
				for status in (*TASK_STATUSES, *custom)
				if status in tasks
			],
			"total": len(self.overview.tasks),
		}

	def by_assignee(self) -> dict:
		"""Open tasks per assignee and how many of them are overdue; busiest first, Unassigned last.

		A task shared by several people counts for each of them. Group tasks are left out, as their
		subtasks carry the work. Each row lists its tasks so its link opens exactly what it counts.
		"""
		rows = {}
		for task in self.workload_tasks:
			for user in task.assigned_to or [None]:
				row = rows.setdefault(user, {"user": user, "open": 0, "overdue": 0, "tasks": []})
				row["open"] += 1
				row["overdue"] += self.overview.is_overdue(task)
				row["tasks"].append(task.name)

		return {
			"rows": sorted(
				rows.values(), key=lambda row: (row["user"] is None, -row["open"], -row["overdue"])
			)
		}

	def by_delivery(self) -> dict:
		"""For a completed or cancelled project, its tasks by how they ended: on time, late, without a date to
		judge, still open, or cancelled. Each outcome lists its tasks, as no list filter can tell on time
		from late."""
		tasks = {}
		for task in self.overview.tasks:
			tasks.setdefault(self.outcome(task), []).append(task.name)
		return {
			"outcomes": [
				{"outcome": outcome, "count": len(tasks[outcome]), "tasks": tasks[outcome]}
				for outcome in DELIVERY_OUTCOMES
				if outcome in tasks
			],
			"total": len(self.overview.tasks),
		}

	def by_completer(self) -> dict:
		"""For a completed or cancelled project, completed tasks per assignee and how many of them were late; most first.

		Completing a task closes its assignments, which empties its Assigned To, so the people are read
		from its ToDos as well; each row lists its tasks, as no list filter can find them that way.
		Group tasks are left out, as their subtasks carry the work.
		"""
		completed = [task for task in self.overview.tasks if task.status == "Completed" and not task.is_group]
		assignees = self.assignees(completed)
		rows = {}
		for task in completed:
			for user in sorted(assignees[task.name]) or [None]:
				row = rows.setdefault(user, {"user": user, "completed": 0, "late": 0, "tasks": []})
				row["completed"] += 1
				row["late"] += self.overview.finished_late(task)
				row["tasks"].append(task.name)

		return {
			"rows": sorted(
				rows.values(), key=lambda row: (row["user"] is None, -row["completed"], row["late"])
			)
		}

	def assignees(self, tasks: list[frappe._dict]) -> dict[str, set[str]]:
		"""Everyone assigned to each task, including assignments closed when it was completed."""
		people = {task.name: set(task.assigned_to) for task in tasks}
		if not tasks:
			return people
		for todo in frappe.get_all(
			"ToDo",
			filters={
				"reference_type": "Task",
				"reference_name": ["in", list(people)],
				"status": ["!=", "Cancelled"],
			},
			fields=["reference_name", "allocated_to"],
		):
			people[todo.reference_name].add(todo.allocated_to)
		return people

	def outcome(self, task: frappe._dict) -> str:
		if task.status == "Cancelled":
			return "Cancelled"
		if task.status != "Completed":
			return "Still Open"
		if not self.overview.can_be_late(task):
			return "No Due Date"
		return "Late" if self.overview.finished_late(task) else "On Time"

	def status(self, task: frappe._dict) -> str:
		return task.status if task.is_closed else self.overview.open_status(task)

	@cached_property
	def workload_tasks(self) -> list[frappe._dict]:
		return [task for task in self.overview.open_tasks if not task.is_group]
