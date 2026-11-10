# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from datetime import date
from functools import cached_property
from itertools import groupby
from math import ceil
from operator import itemgetter

import frappe
from frappe.utils import add_days, date_diff, flt, getdate

STEP_DAYS = 7
MAX_POINTS = 60
CLOSED_PROJECT_STATUSES = ("Completed", "Cancelled")


class PlannedVsCompleted:
	"""Cumulative % complete over time, for the Planned vs Completed chart of a project's Overview tab.

	Planned counts each task as done on its Expected End Date; Completed on its Completed On date, or
	its last modified date when that is missing. Tasks are weighed the way Project.get_task_progress
	weighs them for the project's % Complete method, and the open tasks' own progress is counted at
	the latest point, so the chart ends where the project's % Complete stands.
	"""

	def __init__(self, project: frappe._dict, tasks: list[frappe._dict], today: date):
		self.project = project
		self.tasks = tasks
		self.today = today
		self.method = project.percent_complete_method

	def build(self) -> dict:
		# cancelled tasks count as closed, so only cancelled tasks would chart as 100% done
		if (
			self.method == "Manual"
			or self.project.status == "Cancelled"
			or all(task.status == "Cancelled" for task in self.tasks)
		):
			return {"method": self.method, "points": []}

		dates = self.axis_dates()
		latest = max((on for on in dates if on <= self.today), default=None)
		return {
			"method": self.method,
			"points": [self.point(on, on == latest) for on in dates],
			"today_index": self.today_index(dates),
			"has_plan": self.has_plan,
			"undated": sum(1 for task in self.tasks if not task.due_date),
			"total": len(self.tasks),
			"completed_without_date": sum(
				1 for task in self.tasks if task.status == "Completed" and not task.completed_on
			),
			"worst_gap": self.worst_gap() if self.project.status == "Completed" and self.has_plan else None,
		}

	def worst_gap(self) -> dict:
		"""How far Completed fell behind Planned at worst, and on which date (no date if never behind).

		Checked on every planned date rather than the chart's points, which are a week or more apart, so
		a task due one day and finished the next still counts; the gap can only grow when Planned does.
		"""
		total = sum(self.weights.values())
		planned = sorted((self.planned_date(task), self.weights[task.name]) for task in self.tasks)
		completed = sorted(
			(self.closed_date(task), self.weights[task.name]) for task in self.tasks if task.is_closed
		)
		worst, worst_on = 0, None
		planned_weight = completed_weight = 0
		done = 0
		for on, due in groupby(planned, key=itemgetter(0)):
			if on > self.today:
				break
			planned_weight += sum(weight for _, weight in due)
			while done < len(completed) and completed[done][0] <= on:
				completed_weight += completed[done][1]
				done += 1
			gap = (planned_weight - completed_weight) / total * 100 if total else 0
			if gap > worst:
				worst, worst_on = gap, on
		return {"points": flt(worst, 1), "date": str(worst_on) if worst_on else None}

	def point(self, on: date, is_latest: bool) -> dict:
		"""The latest point up to today shows the project as it stands today; later ones have no Completed."""
		completed = None
		if on <= self.today:
			completed = self.percent(self.completed_weight(self.today if is_latest else on, is_latest))
		return {
			"date": str(on),
			"planned": self.percent(self.planned_weight(on)) if self.has_plan else None,
			"completed": completed,
		}

	def planned_weight(self, on: date) -> float:
		return sum(self.weights[task.name] for task in self.tasks if self.planned_date(task) <= on)

	def completed_weight(self, on: date, with_progress: bool) -> float:
		done = sum(
			self.weights[task.name] for task in self.tasks if task.is_closed and self.closed_date(task) <= on
		)
		return done + (self.open_progress if with_progress else 0)

	@cached_property
	def open_progress(self) -> float:
		"""Partial progress of open tasks; Task Completion counts finished tasks only."""
		if self.method == "Task Completion":
			return 0
		return sum(
			self.weights[task.name] * flt(task.progress) / 100 for task in self.tasks if not task.is_closed
		)

	def percent(self, weight: float) -> float:
		total = sum(self.weights.values())
		return flt(weight / total * 100, 1) if total else 0

	def today_index(self, dates: list[date]) -> int | None:
		"""Today's point, for the Today marker; none once the project is closed."""
		if self.project.status in CLOSED_PROJECT_STATUSES or self.today not in dates:
			return None
		return dates.index(self.today)

	def axis_dates(self) -> list[date]:
		"""Evenly spaced points covering the project, with whole steps at both ends.

		While the project is open the grid runs through today, so the Completed line ends right on
		the Today marker; otherwise it starts at the project's start.
		"""
		span = date_diff(self.axis_end, self.axis_start)
		step = STEP_DAYS * max(1, ceil(span / (STEP_DAYS * MAX_POINTS)))
		anchor = self.axis_start
		if (
			self.project.status not in CLOSED_PROJECT_STATUSES
			and self.axis_start <= self.today <= self.axis_end
		):
			anchor = self.today

		steps_before = ceil(date_diff(anchor, self.axis_start) / step)
		steps_after = ceil(date_diff(self.axis_end, anchor) / step)
		return [getdate(add_days(anchor, offset * step)) for offset in range(-steps_before, steps_after + 1)]

	@cached_property
	def axis_start(self) -> date:
		"""The project's Expected Start, or its earliest task date, pulled back to any task completed
		before it and to today while the project is open, so work done ahead of the plan still shows."""
		if self.project.expected_start_date:
			starts = [getdate(self.project.expected_start_date)]
		else:
			starts = list(self.task_dates)
		starts += [self.closed_date(task) for task in self.tasks if task.status == "Completed"]
		if self.project.status not in CLOSED_PROJECT_STATUSES:
			starts.append(self.today)
		return min(starts, default=self.today)

	@cached_property
	def axis_end(self) -> date:
		"""The latest of the project's Expected End, any task date, and today while the project is open."""
		ends = [*self.task_dates, self.axis_start]
		if self.project.expected_end_date:
			ends.append(getdate(self.project.expected_end_date))
		if self.project.status not in CLOSED_PROJECT_STATUSES:
			ends.append(self.today)
		return max(ends)

	@cached_property
	def task_dates(self) -> list[date]:
		"""Dates the chart must cover. A cancellation is left out: it has no date of its own, and
		its last change can come long after the project ended."""
		dates = [task.due_date for task in self.tasks if task.due_date]
		dates += [getdate(task.exp_start_date) for task in self.tasks if task.exp_start_date]
		dates += [self.closed_date(task) for task in self.tasks if task.status == "Completed"]
		return dates

	@cached_property
	def has_plan(self) -> bool:
		"""Planned is drawn only once at least half the tasks have an Expected End Date."""
		dated = sum(1 for task in self.tasks if task.due_date)
		return dated * 2 >= len(self.tasks)

	def planned_date(self, task: frappe._dict) -> date:
		"""Undated tasks are planned for the project's Expected End, or the end of the chart."""
		if task.due_date:
			return task.due_date
		if self.project.expected_end_date:
			return getdate(self.project.expected_end_date)
		return self.axis_end

	def closed_date(self, task: frappe._dict) -> date:
		"""Completed On, or the last change; a cancelled task counts by the chart's end at the latest."""
		closed_on = getdate(task.completed_on or task.modified)
		if task.status == "Cancelled":
			return min(closed_on, self.axis_end)
		return closed_on

	@cached_property
	def weights(self) -> dict[str, float]:
		weights = {task.name: flt(task.task_weight) for task in self.tasks}
		if self.method != "Task Weight" or not sum(weights.values()):
			return dict.fromkeys(weights, 1.0)
		return weights
