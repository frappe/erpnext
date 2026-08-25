# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import annotations

import datetime
import itertools
from collections import defaultdict

from erpnext.manufacturing.scheduling.models import (
	BACKWARD,
	FINITE,
	FORWARD,
	INFINITE,
	Assignment,
	Interval,
	Resource,
	ScheduleResult,
	Task,
)


class SchedulingEngine:
	def __init__(
		self,
		resources: list[Resource],
		existing_load: dict[str, list[Interval]] | None = None,
		mode: str = FINITE,
		gap_mins: float = 0,
		horizon_days: int = 365,
	):
		self.resources = {resource.name: resource for resource in resources}
		self.mode = mode
		self.gap_mins = gap_mins
		self.horizon_days = horizon_days
		self.load: dict[str, list[Interval]] = defaultdict(list)
		for name, intervals in (existing_load or {}).items():
			self.load[name].extend(intervals)

	def schedule(
		self,
		tasks: list[Task],
		anchor: datetime.datetime,
		direction: str = FORWARD,
		not_before: datetime.datetime | None = None,
	) -> ScheduleResult:
		if direction == BACKWARD:
			return self.schedule_backward(tasks, anchor, not_before)

		return self.schedule_forward(tasks, anchor)

	def schedule_forward(self, tasks: list[Task], anchor: datetime.datetime) -> ScheduleResult:
		result = ScheduleResult(direction_used=FORWARD)
		ordered, cyclic = topological_order(tasks)
		for key in cyclic:
			result.unscheduled[key] = "cycle in dependencies"

		for task in ordered:
			ready_time = self.get_ready_time(task, anchor, result)
			if ready_time is None:
				result.unscheduled[task.key] = "dependency not scheduled"
				continue

			self.place_task(task, ready_time, result)

		return result

	def get_ready_time(self, task, anchor, result):
		ready_time = max(anchor, task.earliest_start or anchor)
		for dependency in task.depends_on:
			assignment = result.assignments.get(dependency)
			if not assignment:
				return None

			dependency_end = assignment.end + datetime.timedelta(minutes=self.gap_mins)
			ready_time = max(ready_time, dependency_end)

		return ready_time

	def place_task(self, task, ready_time, result):
		best = None
		for resource in self.get_candidate_resources(task):
			blocks = self.allocate(resource, ready_time, task.duration_mins, forward=True)
			if blocks and (best is None or blocks[-1].end < best[1][-1].end):
				best = (resource, blocks)

		if best is None:
			result.unscheduled[task.key] = "no capacity within horizon"
			return

		resource, blocks = best
		self.record_blocks(resource, blocks)
		result.assignments[task.key] = Assignment(
			task_key=task.key, resource=resource.name if resource else None, blocks=blocks
		)

	def schedule_backward(
		self,
		tasks: list[Task],
		due_anchor: datetime.datetime,
		not_before: datetime.datetime | None = None,
	) -> ScheduleResult:
		snapshot = {name: list(intervals) for name, intervals in self.load.items()}
		result = self.try_backward(tasks, due_anchor, not_before)
		if result is not None:
			return result

		self.load = defaultdict(list)
		for name, intervals in snapshot.items():
			self.load[name].extend(intervals)

		return self.schedule_forward(tasks, not_before)

	def try_backward(self, tasks, due_anchor, not_before):
		result = ScheduleResult(direction_used=BACKWARD)
		ordered, cyclic = topological_order(tasks)
		for key in cyclic:
			result.unscheduled[key] = "cycle in dependencies"

		successors = get_successor_map(tasks)
		for task in reversed(ordered):
			latest_end = self.get_latest_end(task, due_anchor, successors, result)
			if latest_end is None:
				result.unscheduled[task.key] = "dependent not scheduled"
				continue

			if not self.place_task_backward(task, latest_end, not_before, result):
				if not_before is None:
					result.unscheduled[task.key] = "no capacity before due date"
					continue

				return None

		return result

	def get_latest_end(self, task, due_anchor, successors, result):
		latest_end = min(due_anchor, task.due_date or due_anchor)
		for successor in successors.get(task.key, []):
			assignment = result.assignments.get(successor)
			if not assignment:
				return None

			successor_start = assignment.start - datetime.timedelta(minutes=self.gap_mins)
			latest_end = min(latest_end, successor_start)

		return latest_end

	def place_task_backward(self, task, latest_end, not_before, result):
		best = None
		for resource in self.get_candidate_resources(task):
			blocks = self.allocate(resource, latest_end, task.duration_mins, forward=False)
			if blocks and (best is None or blocks[0].start > best[1][0].start):
				best = (resource, blocks)

		bounds = [bound for bound in (task.earliest_start, not_before) if bound]
		earliest_bound = max(bounds, default=None)
		if best is None or (earliest_bound and best[1][0].start < earliest_bound):
			return False

		resource, blocks = best
		self.record_blocks(resource, blocks)
		result.assignments[task.key] = Assignment(
			task_key=task.key, resource=resource.name if resource else None, blocks=blocks
		)
		return True

	def get_candidate_resources(self, task):
		if task.resource:
			return [self.resources[task.resource]] if task.resource in self.resources else []

		if task.resource_type:
			return [r for r in self.resources.values() if r.resource_type == task.resource_type]

		return [None]

	def allocate(self, resource, anchor, duration_mins, forward=True):
		if resource is None:
			return [continuous_block(anchor, duration_mins, forward)]

		blocks = []
		remaining = duration_mins
		day, boundary = anchor.date(), anchor
		for _ in range(self.horizon_days):
			windows = resource.calendar.windows_for_day(day)
			for window in windows if forward else reversed(windows):
				taken, remaining = self.consume_window(resource, window, boundary, remaining, forward)
				blocks.extend(taken)
				if remaining <= 0:
					blocks.sort(key=lambda block: block.start)
					return blocks

			day += datetime.timedelta(days=1 if forward else -1)

		return None

	def consume_window(self, resource, window, boundary, remaining, forward):
		start = max(window.start, boundary) if forward else window.start
		end = window.end if forward else min(window.end, boundary)
		if end <= start:
			return [], remaining

		blocks = []
		segments = self.free_segments(resource, start, end)
		for segment_start, segment_end in segments if forward else reversed(segments):
			take_mins = min(remaining, (segment_end - segment_start).total_seconds() / 60)
			if take_mins <= 0:
				continue

			blocks.append(cut_segment(segment_start, segment_end, take_mins, forward))
			remaining -= take_mins
			if remaining <= 0:
				break

		return blocks, remaining

	def free_segments(self, resource, start, end):
		if self.mode == INFINITE:
			return [(start, end)]

		overlapping = [iv for iv in self.load.get(resource.name, []) if iv.start < end and iv.end > start]
		points = sorted(
			{start, end}
			| {max(iv.start, start) for iv in overlapping}
			| {min(iv.end, end) for iv in overlapping}
		)

		segments = []
		for segment_start, segment_end in itertools.pairwise(points):
			concurrent = sum(1 for iv in overlapping if iv.start < segment_end and iv.end > segment_start)
			if concurrent < resource.capacity:
				if segments and segments[-1][1] == segment_start:
					segments[-1] = (segments[-1][0], segment_end)
				else:
					segments.append((segment_start, segment_end))

		return segments

	def record_blocks(self, resource, blocks):
		if resource is not None:
			self.load[resource.name].extend(blocks)


def continuous_block(anchor, duration_mins, forward):
	delta = datetime.timedelta(minutes=duration_mins)
	return Interval(anchor, anchor + delta) if forward else Interval(anchor - delta, anchor)


def cut_segment(segment_start, segment_end, take_mins, forward):
	delta = datetime.timedelta(minutes=take_mins)
	if forward:
		return Interval(segment_start, segment_start + delta)

	return Interval(segment_end - delta, segment_end)


def topological_order(tasks: list[Task]) -> tuple[list[Task], list[str]]:
	by_key = {task.key: task for task in tasks}
	pending_deps = {task.key: {dep for dep in task.depends_on if dep in by_key} for task in tasks}
	dependents = defaultdict(list)
	for task in tasks:
		for dep in pending_deps[task.key]:
			dependents[dep].append(task.key)

	ready = sorted(
		(key for key, deps in pending_deps.items() if not deps),
		key=lambda key: (-by_key[key].priority, key),
	)
	ordered = []
	while ready:
		key = ready.pop(0)
		ordered.append(by_key[key])
		for dependent in dependents[key]:
			pending_deps[dependent].discard(key)
			if not pending_deps[dependent]:
				insert_by_priority(ready, dependent, by_key)

	cyclic = [key for key, deps in pending_deps.items() if deps]
	return ordered, cyclic


def insert_by_priority(ready: list[str], key: str, by_key: dict[str, Task]):
	rank = (-by_key[key].priority, key)
	index = 0
	while index < len(ready) and (-by_key[ready[index]].priority, ready[index]) < rank:
		index += 1

	ready.insert(index, key)


def get_successor_map(tasks: list[Task]) -> dict[str, list[str]]:
	successors = defaultdict(list)
	for task in tasks:
		for dependency in task.depends_on:
			successors[dependency].append(task.key)

	return successors
