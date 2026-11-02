# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import datetime
import unittest

from erpnext.manufacturing.scheduling.engine import SchedulingEngine
from erpnext.manufacturing.scheduling.models import (
	BACKWARD,
	FORWARD,
	INFINITE,
	Interval,
	Resource,
	ResourceCalendar,
	Task,
)


def dt(day, hour, minute=0):
	return datetime.datetime(2026, 8, day, hour, minute)


def day_shift_calendar():
	return ResourceCalendar(daily_windows=[(datetime.time(9, 0), datetime.time(17, 0))])


class TestSchedulingEngine(unittest.TestCase):
	def test_forward_places_task_within_working_window(self):
		engine = SchedulingEngine([Resource("WS-A", calendar=day_shift_calendar())])
		result = engine.schedule([Task("t1", duration_mins=120, resource="WS-A")], anchor=dt(12, 10))

		assignment = result.assignments["t1"]
		self.assertEqual(assignment.start, dt(12, 10))
		self.assertEqual(assignment.end, dt(12, 12))

	def test_task_splits_across_days_and_skips_holiday(self):
		calendar = day_shift_calendar()
		calendar.holidays.add(datetime.date(2026, 8, 13))
		engine = SchedulingEngine([Resource("WS-A", calendar=calendar)])

		result = engine.schedule([Task("t1", duration_mins=600, resource="WS-A")], anchor=dt(12, 15))

		blocks = result.assignments["t1"].blocks
		self.assertEqual(blocks[0], Interval(dt(12, 15), dt(12, 17)))
		self.assertEqual(blocks[1], Interval(dt(14, 9), dt(14, 17)))
		self.assertEqual(result.assignments["t1"].end, dt(14, 17))

	def test_finite_capacity_serializes_and_capacity_two_runs_parallel(self):
		tasks = [
			Task("t1", duration_mins=120, resource="WS-A"),
			Task("t2", duration_mins=120, resource="WS-A"),
		]

		engine = SchedulingEngine([Resource("WS-A", calendar=day_shift_calendar(), capacity=1)])
		result = engine.schedule([*tasks], anchor=dt(12, 9))
		self.assertEqual(result.assignments["t1"].start, dt(12, 9))
		self.assertEqual(result.assignments["t2"].start, dt(12, 11))

		engine = SchedulingEngine([Resource("WS-A", calendar=day_shift_calendar(), capacity=2)])
		result = engine.schedule([*tasks], anchor=dt(12, 9))
		self.assertEqual(result.assignments["t2"].start, dt(12, 9))

	def test_existing_load_pushes_task_and_infinite_mode_ignores_it(self):
		booked = {"WS-A": [Interval(dt(12, 9), dt(12, 12))]}

		engine = SchedulingEngine([Resource("WS-A", calendar=day_shift_calendar())], existing_load=booked)
		result = engine.schedule([Task("t1", duration_mins=60, resource="WS-A")], anchor=dt(12, 9))
		self.assertEqual(result.assignments["t1"].start, dt(12, 12))

		engine = SchedulingEngine(
			[Resource("WS-A", calendar=day_shift_calendar())], existing_load=booked, mode=INFINITE
		)
		result = engine.schedule([Task("t1", duration_mins=60, resource="WS-A")], anchor=dt(12, 9))
		self.assertEqual(result.assignments["t1"].start, dt(12, 9))

	def test_dependency_chain_applies_gap(self):
		engine = SchedulingEngine([Resource("WS-A", calendar=day_shift_calendar())], gap_mins=10)
		tasks = [
			Task("t1", duration_mins=60, resource="WS-A"),
			Task("t2", duration_mins=60, resource="WS-A", depends_on=["t1"]),
		]

		result = engine.schedule(tasks, anchor=dt(12, 9))
		self.assertEqual(result.assignments["t2"].start, dt(12, 10, 10))

	def test_capability_selection_picks_free_machine(self):
		resources = [
			Resource("WS-A", calendar=day_shift_calendar(), resource_type="CNC"),
			Resource("WS-B", calendar=day_shift_calendar(), resource_type="CNC"),
		]
		engine = SchedulingEngine(resources, existing_load={"WS-A": [Interval(dt(12, 9), dt(12, 13))]})

		result = engine.schedule([Task("t1", duration_mins=60, resource_type="CNC")], anchor=dt(12, 9))
		self.assertEqual(result.assignments["t1"].resource, "WS-B")
		self.assertEqual(result.assignments["t1"].start, dt(12, 9))

	def test_four_jobs_run_concurrently_on_two_capacity_two_machines(self):
		resources = [
			Resource("Mold-A", calendar=day_shift_calendar(), capacity=2, resource_type="Molding"),
			Resource("Mold-B", calendar=day_shift_calendar(), capacity=2, resource_type="Molding"),
		]
		engine = SchedulingEngine(resources)
		tasks = [Task(f"t{i}", duration_mins=120, resource_type="Molding") for i in range(4)]

		result = engine.schedule(tasks, anchor=dt(12, 9))

		self.assertEqual([a.start for a in result.assignments.values()], [dt(12, 9)] * 4)
		machines = sorted(a.resource for a in result.assignments.values())
		self.assertEqual(machines, ["Mold-A", "Mold-A", "Mold-B", "Mold-B"])

		overflow = engine.schedule([Task("t5", duration_mins=120, resource_type="Molding")], anchor=dt(12, 9))
		self.assertEqual(overflow.assignments["t5"].start, dt(12, 11))

	def test_priority_wins_contention(self):
		tasks = [
			Task("low", duration_mins=120, resource="WS-A", priority=1),
			Task("high", duration_mins=120, resource="WS-A", priority=10),
		]
		engine = SchedulingEngine([Resource("WS-A", calendar=day_shift_calendar())])

		result = engine.schedule(tasks, anchor=dt(12, 9))
		self.assertEqual(result.assignments["high"].start, dt(12, 9))
		self.assertEqual(result.assignments["low"].start, dt(12, 11))

	def test_backward_scheduling_meets_due_date(self):
		engine = SchedulingEngine([Resource("WS-A", calendar=day_shift_calendar())], gap_mins=10)
		tasks = [
			Task("t1", duration_mins=60, resource="WS-A"),
			Task("t2", duration_mins=120, resource="WS-A", depends_on=["t1"]),
		]

		result = engine.schedule(tasks, anchor=dt(14, 17), direction=BACKWARD, not_before=dt(12, 9))

		self.assertEqual(result.direction_used, BACKWARD)
		self.assertEqual(result.assignments["t2"].end, dt(14, 17))
		self.assertEqual(result.assignments["t2"].start, dt(14, 15))
		self.assertEqual(result.assignments["t1"].end, dt(14, 14, 50))
		self.assertEqual(result.assignments["t1"].start, dt(14, 13, 50))

	def test_backward_falls_back_forward_when_due_date_infeasible(self):
		engine = SchedulingEngine([Resource("WS-A", calendar=day_shift_calendar())])
		tasks = [Task("t1", duration_mins=480, resource="WS-A")]

		result = engine.schedule(tasks, anchor=dt(12, 11), direction=BACKWARD, not_before=dt(12, 9))

		self.assertEqual(result.direction_used, FORWARD)
		self.assertEqual(result.assignments["t1"].start, dt(12, 9))
		self.assertEqual(result.assignments["t1"].end, dt(12, 17))

	def test_calendarless_task_runs_continuously(self):
		engine = SchedulingEngine([])
		result = engine.schedule([Task("buy", duration_mins=2880)], anchor=dt(12, 8))

		self.assertIsNone(result.assignments["buy"].resource)
		self.assertEqual(result.assignments["buy"].end, dt(14, 8))

	def test_cycle_and_missing_capacity_reported_not_raised(self):
		engine = SchedulingEngine([Resource("WS-A", calendar=day_shift_calendar())], horizon_days=1)
		tasks = [
			Task("a", duration_mins=60, resource="WS-A", depends_on=["b"]),
			Task("b", duration_mins=60, resource="WS-A", depends_on=["a"]),
			Task("c", duration_mins=600, resource="WS-A"),
		]

		result = engine.schedule(tasks, anchor=dt(12, 9))

		self.assertIn("a", result.unscheduled)
		self.assertIn("b", result.unscheduled)
		self.assertEqual(result.unscheduled["c"], "no capacity within horizon")

	def test_run_holds_multiple_documents_without_blind_spots(self):
		engine = SchedulingEngine([Resource("WS-A", calendar=day_shift_calendar())])
		plan_a = [Task("planA:op", duration_mins=240, resource="WS-A")]
		plan_b = [Task("planB:op", duration_mins=240, resource="WS-A")]

		result_a = engine.schedule(plan_a, anchor=dt(12, 9))
		result_b = engine.schedule(plan_b, anchor=dt(12, 9))

		self.assertEqual(result_a.assignments["planA:op"].start, dt(12, 9))
		self.assertEqual(result_b.assignments["planB:op"].start, dt(12, 13))


if __name__ == "__main__":
	unittest.main()
