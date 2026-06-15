# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
import frappe
from frappe import _
from frappe.utils import getdate

from erpnext.manufacturing.doctype.operation.test_operation import make_operation
from erpnext.manufacturing.doctype.routing.test_routing import create_routing, setup_bom
from erpnext.manufacturing.doctype.workstation.workstation import (
	NotInWorkingHoursError,
	OverlapError,
	WorkstationHolidayError,
	check_if_within_operating_hours,
	check_workstation_for_holiday,
	get_color_map,
	get_status_color,
	is_within_operating_hours,
	update_job_card,
)
from erpnext.manufacturing.doctype.workstation_type.test_workstation_type import (
	create_workstation_type,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestWorkstation(ERPNextTestSuite):
	def test_update_job_card_rejects_disallowed_method(self):
		# The whitelisted update_job_card endpoint must only run an allowlisted set of Job Card
		# methods. An arbitrary method name must be rejected (PermissionError) before the document
		# is even loaded, so this needs no Job Card to exist.
		self.assertRaises(
			frappe.PermissionError,
			update_job_card,
			"NON-EXISTENT-JOB-CARD",
			"delete",
		)

	def test_validate_timings(self):
		check_if_within_operating_hours(
			"_Test Workstation 1", "Operation 1", "2013-02-02 11:00:00", "2013-02-02 19:00:00"
		)
		check_if_within_operating_hours(
			"_Test Workstation 1", "Operation 1", "2013-02-02 10:00:00", "2013-02-02 20:00:00"
		)
		self.assertRaises(
			NotInWorkingHoursError,
			check_if_within_operating_hours,
			"_Test Workstation 1",
			"Operation 1",
			"2013-02-02 05:00:00",
			"2013-02-02 20:00:00",
		)
		self.assertRaises(
			NotInWorkingHoursError,
			check_if_within_operating_hours,
			"_Test Workstation 1",
			"Operation 1",
			"2013-02-02 05:00:00",
			"2013-02-02 20:00:00",
		)
		self.assertRaises(
			WorkstationHolidayError,
			check_if_within_operating_hours,
			"_Test Workstation 1",
			"Operation 1",
			"2013-02-01 10:00:00",
			"2013-02-02 20:00:00",
		)

	def test_update_bom_operation_rate(self):
		operations = [
			{
				"operation": "Test Operation A",
				"workstation": "_Test Workstation A",
				"hour_rate_rent": 300,
				"time_in_mins": 60,
			},
			{
				"operation": "Test Operation B",
				"workstation": "_Test Workstation B",
				"hour_rate_rent": 1000,
				"time_in_mins": 60,
			},
		]

		for row in operations:
			make_workstation(row)
			make_operation(row)

		test_routing_operations = [
			{"operation": "Test Operation A", "workstation": "_Test Workstation A", "time_in_mins": 60},
			{"operation": "Test Operation B", "workstation": "_Test Workstation A", "time_in_mins": 60},
		]
		routing_doc = create_routing(routing_name="Routing Test", operations=test_routing_operations)
		bom_doc = setup_bom(item_code="_Testing Item", routing=routing_doc.name, currency="INR")
		w1 = frappe.get_doc("Workstation", "_Test Workstation A")
		# resets values
		for row in w1.workstation_costs:
			if row.operating_component == _("Rent"):
				row.operating_cost = 300
				break

		w1.save()
		bom_doc.update_cost()
		bom_doc.reload()
		self.assertEqual(w1.hour_rate, 300)
		self.assertEqual(bom_doc.operations[0].hour_rate, 300)

		for row in w1.workstation_costs:
			if row.operating_component == _("Rent"):
				row.operating_cost = 250
				break

		w1.save()
		# updating after setting new rates in workstations
		bom_doc.update_cost()
		bom_doc.reload()
		self.assertEqual(w1.hour_rate, 250)
		self.assertEqual(bom_doc.operations[0].hour_rate, 250)
		self.assertEqual(bom_doc.operations[1].hour_rate, 250)


def make_workstation(*args, **kwargs):
	args = args if args else kwargs
	if isinstance(args, tuple):
		args = args[0]

	args = frappe._dict(args)

	workstation_name = args.workstation_name or args.workstation
	if not frappe.db.exists("Workstation", workstation_name):
		doc = frappe.get_doc({"doctype": "Workstation", "workstation_name": workstation_name})
		if args.get("hour_rate_rent"):
			doc.append(
				"workstation_costs",
				{
					"operating_component": _("Rent"),
					"operating_cost": args.get("hour_rate_rent"),
				},
			)

		if args.get("hour_rate_labour"):
			doc.append(
				"workstation_costs",
				{
					"operating_component": _("Wages"),
					"operating_cost": args.get("hour_rate_labour"),
				},
			)

		doc.workstation_type = args.get("workstation_type")
		doc.insert()

		return doc

	return frappe.get_doc("Workstation", workstation_name)


class TestWorkstationCoverage(ERPNextTestSuite):
	"""Coverage for Workstation capacity / working-hours logic.

	These tests exercise the pure colour helpers, the working-hours total/validation,
	the overlap guard, the operating-hours fit check and the holiday handling. They build
	their own Workstation docs (with unique names so repeated runs do not collide with
	stale rows) instead of relying on shared fixture state, except where the documented
	module functions need a persisted record to query.
	"""

	def _make_workstation_with_hours(self, name, hours):
		"""Create (or fetch) a Workstation with the given list of (start, end) tuples
		as working_hours rows, then save so the rows are persisted in the DB.

		The DB is rolled back in tearDown so the record never leaks between tests.
		"""
		doc = make_workstation({"workstation_name": name})
		# Start from a clean slate so re-fetching an existing fixture row is deterministic.
		doc.set("working_hours", [])
		for start_time, end_time in hours:
			doc.append("working_hours", {"start_time": start_time, "end_time": end_time})
		doc.save()
		return doc

	# ------------------------------------------------------------------ #
	# get_status_color / get_color_map: pure functions, fully deterministic.
	# ------------------------------------------------------------------ #
	def test_get_status_color_known_statuses(self):
		expected = {
			"Pending": "blue",
			"In Process": "yellow",
			"Submitted": "blue",
			"Open": "gray",
			"Closed": "green",
			"Work In Progress": "orange",
		}
		for status, colour in expected.items():
			self.assertEqual(get_status_color(status), colour)

	def test_get_status_color_unknown_falls_back_to_blue(self):
		# Any status not in the map (incl. None) must fall back to the default "blue".
		self.assertEqual(get_status_color("Some Unknown Status"), "blue")
		self.assertEqual(get_status_color(None), "blue")

	def test_get_color_map_contents(self):
		# get_color_map drives the Plant Floor workstation status colours.
		color_map = get_color_map()
		self.assertEqual(
			color_map,
			{
				"Production": "green",
				"Off": "gray",
				"Idle": "gray",
				"Problem": "red",
				"Maintenance": "yellow",
				"Setup": "blue",
			},
		)
		# A status missing from the map resolves to "red" at the call sites that use .get(..., "red").
		self.assertIsNone(color_map.get("Nonexistent"))

	# ------------------------------------------------------------------ #
	# set_total_working_hours / validate_working_hours
	# ------------------------------------------------------------------ #
	def test_set_total_working_hours_sums_each_slot(self):
		# 09:00-17:00 = 8h, 18:00-20:30 = 2.5h -> total 10.5h. The calc runs in before_save
		# but is also callable directly on an in-memory doc; assert the persisted total too.
		doc = self._make_workstation_with_hours(
			"_Test WS Cov Hours", [("09:00:00", "17:00:00"), ("18:00:00", "20:30:00")]
		)
		self.assertAlmostEqual(doc.total_working_hours, 10.5, places=2)
		# Per-row hours are populated as a side effect.
		row_hours = sorted(row.hours for row in doc.working_hours)
		self.assertAlmostEqual(row_hours[0], 2.5, places=2)
		self.assertAlmostEqual(row_hours[1], 8.0, places=2)

	def test_set_total_working_hours_single_slot(self):
		doc = self._make_workstation_with_hours("_Test WS Cov Single", [("09:00:00", "17:00:00")])
		self.assertAlmostEqual(doc.total_working_hours, 8.0, places=2)

	def test_validate_working_hours_start_after_end_raises(self):
		# A row whose start_time is not strictly before end_time must be rejected.
		doc = make_workstation({"workstation_name": "_Test WS Cov BadTimes"})
		doc.set("working_hours", [])
		row = doc.append("working_hours", {"start_time": "18:00:00", "end_time": "09:00:00"})
		self.assertRaises(frappe.ValidationError, doc.validate_working_hours, row)

	def test_validate_working_hours_equal_times_raises(self):
		# start_time == end_time is also invalid (the guard is >=, a zero-length slot).
		doc = make_workstation({"workstation_name": "_Test WS Cov EqualTimes"})
		doc.set("working_hours", [])
		row = doc.append("working_hours", {"start_time": "09:00:00", "end_time": "09:00:00"})
		self.assertRaises(frappe.ValidationError, doc.validate_working_hours, row)

	def test_save_with_invalid_times_raises(self):
		# End-to-end: saving a workstation with an inverted slot fails in before_save.
		doc = make_workstation({"workstation_name": "_Test WS Cov SaveBad"})
		doc.set("working_hours", [])
		doc.append("working_hours", {"start_time": "20:00:00", "end_time": "10:00:00"})
		self.assertRaises(frappe.ValidationError, doc.save)

	# ------------------------------------------------------------------ #
	# validate_overlap_for_operation_timings (runs in on_update, queries persisted rows)
	# ------------------------------------------------------------------ #
	def test_non_overlapping_working_hours_save_cleanly(self):
		doc = self._make_workstation_with_hours(
			"_Test WS Cov NoOverlap", [("09:00:00", "12:00:00"), ("13:00:00", "17:00:00")]
		)
		# No exception, and the rows persisted.
		self.assertEqual(len(doc.working_hours), 2)

	def test_overlapping_working_hours_raise_overlap_error(self):
		# 09:00-12:00 and 11:00-15:00 overlap between 11:00 and 12:00.
		doc = make_workstation({"workstation_name": "_Test WS Cov Overlap"})
		doc.set("working_hours", [])
		doc.append("working_hours", {"start_time": "09:00:00", "end_time": "12:00:00"})
		doc.append("working_hours", {"start_time": "11:00:00", "end_time": "15:00:00"})
		self.assertRaises(OverlapError, doc.save)

	# ------------------------------------------------------------------ #
	# is_within_operating_hours: raises NotInWorkingHoursError when the operation cannot
	# fit any single working-hours slot, passes when it fits.
	# ------------------------------------------------------------------ #
	def test_is_within_operating_hours_fits(self):
		# Slot is 8h (09:00-17:00); a 6h operation fits -> no exception.
		self._make_workstation_with_hours("_Test WS Cov Fit", [("09:00:00", "17:00:00")])
		with self.change_settings("Manufacturing Settings", allow_overtime=0):
			is_within_operating_hours(
				"_Test WS Cov Fit",
				"_Test WS Cov Op",
				"2024-01-01 09:00:00",
				"2024-01-01 15:00:00",
			)

	def test_is_within_operating_hours_too_long_raises(self):
		# Slot is 8h; a 10h operation exceeds every slot -> NotInWorkingHoursError.
		self._make_workstation_with_hours("_Test WS Cov TooLong", [("09:00:00", "17:00:00")])
		with self.change_settings("Manufacturing Settings", allow_overtime=0):
			self.assertRaises(
				NotInWorkingHoursError,
				is_within_operating_hours,
				"_Test WS Cov TooLong",
				"_Test WS Cov Op",
				"2024-01-01 08:00:00",
				"2024-01-01 18:00:00",
			)

	def test_is_within_operating_hours_no_working_hours_is_noop(self):
		# With no working_hours rows the function returns early without raising.
		doc = make_workstation({"workstation_name": "_Test WS Cov NoHours"})
		doc.set("working_hours", [])
		doc.save()
		is_within_operating_hours(
			"_Test WS Cov NoHours",
			"_Test WS Cov Op",
			"2024-01-01 08:00:00",
			"2024-01-01 18:00:00",
		)

	# ------------------------------------------------------------------ #
	# Holiday handling: check_workstation_for_holiday (module fn) and
	# validate_workstation_holiday (recursive method that skips holidays).
	# These rely on the shared "_Test Holiday List" fixture (holidays in 2013).
	# ------------------------------------------------------------------ #
	def test_check_workstation_for_holiday_raises_on_holiday(self):
		doc = self._make_workstation_with_hours("_Test WS Cov HolidayRaise", [("09:00:00", "17:00:00")])
		doc.db_set("holiday_list", "_Test Holiday List")
		# 2013-02-01 ("Test Holiday") falls inside the range -> WorkstationHolidayError.
		self.assertRaises(
			WorkstationHolidayError,
			check_workstation_for_holiday,
			doc.name,
			"2013-02-01 10:00:00",
			"2013-02-01 18:00:00",
		)

	def test_check_workstation_for_holiday_passes_when_clear(self):
		doc = self._make_workstation_with_hours("_Test WS Cov HolidayClear", [("09:00:00", "17:00:00")])
		doc.db_set("holiday_list", "_Test Holiday List")
		# 2013-02-05 .. 2013-02-06 contains no fixture holiday -> no exception.
		check_workstation_for_holiday(doc.name, "2013-02-05 10:00:00", "2013-02-06 18:00:00")

	def test_validate_workstation_holiday_skips_to_next_working_day(self):
		# 2013-02-01 is a holiday in the fixture list; the recursion must roll the date
		# forward to the next non-holiday day (2013-02-02).
		doc = make_workstation({"workstation_name": "_Test WS Cov HolidaySkip"})
		doc.db_set("holiday_list", "_Test Holiday List")
		with self.change_settings("Manufacturing Settings", allow_production_on_holidays=0):
			result = doc.validate_workstation_holiday(getdate("2013-02-01"))
		self.assertEqual(result, getdate("2013-02-02"))

	def test_validate_workstation_holiday_returns_same_date_when_not_holiday(self):
		doc = make_workstation({"workstation_name": "_Test WS Cov HolidayKeep"})
		doc.db_set("holiday_list", "_Test Holiday List")
		with self.change_settings("Manufacturing Settings", allow_production_on_holidays=0):
			result = doc.validate_workstation_holiday(getdate("2013-02-05"))
		self.assertEqual(result, getdate("2013-02-05"))

	def test_validate_workstation_holiday_noop_when_production_allowed(self):
		# When production is allowed on holidays the date is returned unchanged even if it
		# is a holiday.
		doc = make_workstation({"workstation_name": "_Test WS Cov HolidayAllowed"})
		doc.db_set("holiday_list", "_Test Holiday List")
		with self.change_settings("Manufacturing Settings", allow_production_on_holidays=1):
			result = doc.validate_workstation_holiday(getdate("2013-02-01"))
		self.assertEqual(result, getdate("2013-02-01"))

	# ------------------------------------------------------------------ #
	# _set_data_based_on_workstation_type: copies operating costs from the linked
	# Workstation Type onto the Workstation and recomputes hour_rate.
	# ------------------------------------------------------------------ #
	def test_set_data_based_on_workstation_type_copies_costs(self):
		ws_type = create_workstation_type(workstation_type="_Test WS Cov Type")
		ws_type.set("workstation_costs", [])
		ws_type.append(
			"workstation_costs",
			{"operating_component": _("Rent"), "operating_cost": 120},
		)
		ws_type.save()

		doc = make_workstation({"workstation_name": "_Test WS Cov FromType"})
		doc.set("workstation_costs", [])
		doc.workstation_type = ws_type.name
		doc._set_data_based_on_workstation_type()

		self.assertEqual(len(doc.workstation_costs), 1)
		self.assertEqual(doc.workstation_costs[0].operating_component, _("Rent"))
		self.assertAlmostEqual(doc.workstation_costs[0].operating_cost, 120, places=2)

		# set_hour_rate sums the operating costs into hour_rate.
		doc.set_hour_rate()
		self.assertAlmostEqual(doc.hour_rate, 120, places=2)

	def test_set_hour_rate_sums_operating_costs(self):
		doc = make_workstation(
			{"workstation_name": "_Test WS Cov HourRate", "hour_rate_rent": 30, "hour_rate_labour": 20}
		)
		doc.set_hour_rate()
		self.assertAlmostEqual(doc.hour_rate, 50, places=2)
