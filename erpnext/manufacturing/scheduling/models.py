# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import annotations

import datetime
from dataclasses import dataclass, field

FORWARD = "Forward"
BACKWARD = "Backward"
FINITE = "Finite"
INFINITE = "Infinite"


@dataclass(frozen=True)
class Interval:
	start: datetime.datetime
	end: datetime.datetime

	def overlaps(self, other: Interval) -> bool:
		return self.start < other.end and self.end > other.start

	def duration_mins(self) -> float:
		return (self.end - self.start).total_seconds() / 60


@dataclass
class ResourceCalendar:
	daily_windows: list[tuple[datetime.time, datetime.time]] = field(default_factory=list)
	holidays: set[datetime.date] = field(default_factory=set)

	def is_always_open(self) -> bool:
		return not self.daily_windows

	def windows_for_day(self, day: datetime.date) -> list[Interval]:
		if day in self.holidays:
			return []

		if self.is_always_open():
			start = datetime.datetime.combine(day, datetime.time.min)
			return [Interval(start, start + datetime.timedelta(days=1))]

		return [
			Interval(datetime.datetime.combine(day, start), datetime.datetime.combine(day, end))
			for start, end in self.daily_windows
			if end > start
		]


@dataclass
class Resource:
	name: str
	calendar: ResourceCalendar = field(default_factory=ResourceCalendar)
	capacity: int = 1
	resource_type: str | None = None


@dataclass
class Task:
	key: str
	duration_mins: float
	resource: str | None = None
	resource_type: str | None = None
	depends_on: list[str] = field(default_factory=list)
	earliest_start: datetime.datetime | None = None
	due_date: datetime.datetime | None = None
	priority: int = 0
	label: str | None = None


@dataclass
class Assignment:
	task_key: str
	resource: str | None
	blocks: list[Interval]

	@property
	def start(self) -> datetime.datetime:
		return self.blocks[0].start

	@property
	def end(self) -> datetime.datetime:
		return self.blocks[-1].end


@dataclass
class ScheduleResult:
	assignments: dict[str, Assignment] = field(default_factory=dict)
	unscheduled: dict[str, str] = field(default_factory=dict)
	direction_used: str = FORWARD

	@property
	def start_date(self) -> datetime.datetime | None:
		starts = [a.start for a in self.assignments.values()]
		return min(starts) if starts else None

	@property
	def end_date(self) -> datetime.datetime | None:
		ends = [a.end for a in self.assignments.values()]
		return max(ends) if ends else None
