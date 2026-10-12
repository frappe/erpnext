# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from collections import Counter
from functools import cached_property
from typing import TYPE_CHECKING

import frappe

if TYPE_CHECKING:
	from erpnext.projects.doctype.project.project_overview import ProjectOverview

# workflow order, so the donut and its legend read from new work to closed work
TASK_STATUSES = ("Open", "Working", "Pending Review", "Overdue", "Completed", "Cancelled")


class TaskBreakdown:
	"""Tasks by Status and Open Tasks by Assignee, for a project's Overview tab.

	Reads the tasks the overview has already loaded, and decides Overdue the way its
	stat cards do.
	"""

	def __init__(self, overview: "ProjectOverview"):
		self.overview = overview

	def by_status(self) -> dict:
		"""Task count per status; an open task past its Expected End Date counts as Overdue."""
		counts = Counter(self.status(task) for task in self.overview.tasks)
		return {
			"statuses": [
				{"status": status, "count": counts[status]} for status in TASK_STATUSES if counts[status]
			],
			"total": len(self.overview.tasks),
		}

	def by_assignee(self) -> dict:
		"""Open tasks per assignee and how many of them are overdue; busiest first, Unassigned last.

		A task shared by several people counts for each of them. Group tasks are left out, as their
		subtasks carry the work.
		"""
		rows = {}
		for task in self.workload_tasks:
			for user in task.assigned_to or [None]:
				row = rows.setdefault(user, {"user": user, "open": 0, "overdue": 0})
				row["open"] += 1
				row["overdue"] += self.overview.is_overdue(task)

		return {
			"rows": sorted(
				rows.values(), key=lambda row: (row["user"] is None, -row["open"], -row["overdue"])
			)
		}

	def status(self, task: frappe._dict) -> str:
		if not task.is_closed and self.overview.is_overdue(task):
			return "Overdue"
		# the daily job may not have reset a task it marked Overdue before its date moved
		return "Open" if task.status == "Overdue" else task.status

	@cached_property
	def workload_tasks(self) -> list[frappe._dict]:
		return [task for task in self.overview.open_tasks if not task.is_group]
