# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from datetime import datetime, timedelta
from typing import Dict, List

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import Criterion
from frappe.utils import cstr, get_datetime, get_link_to_form, get_time, getdate, now_datetime

from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee
from erpnext.hr.doctype.holiday_list.holiday_list import is_holiday
from erpnext.hr.utils import validate_active_employee


class OverlappingShiftError(frappe.ValidationError):
	pass


class ShiftAssignment(Document):
	def validate(self):
		validate_active_employee(self.employee)
		self.validate_overlapping_shifts()

		if self.end_date:
			self.validate_from_to_dates("start_date", "end_date")

	def validate_overlapping_shifts(self):
		overlapping_dates = self.get_overlapping_dates()
		if len(overlapping_dates):
			# if dates are overlapping, check if timings are overlapping, else allow
			overlapping_timings = has_overlapping_timings(self.shift_type, overlapping_dates[0].shift_type)
			if overlapping_timings:
				self.throw_overlap_error(overlapping_dates[0])

	def get_overlapping_dates(self):
		if not self.name:
			self.name = "New Shift Assignment"

		shift = frappe.qb.DocType("Shift Assignment")
		query = (
			frappe.qb.from_(shift)
			.select(shift.name, shift.shift_type, shift.docstatus, shift.status)
			.where(
				(shift.employee == self.employee)
				& (shift.docstatus == 1)
				& (shift.name != self.name)
				& (shift.status == "Active")
			)
		)

		if self.end_date:
			query = query.where(
				Criterion.any(
					[
						Criterion.any(
							[
								shift.end_date.isnull(),
								((self.start_date >= shift.start_date) & (self.start_date <= shift.end_date)),
							]
						),
						Criterion.any(
							[
								((self.end_date >= shift.start_date) & (self.end_date <= shift.end_date)),
								shift.start_date.between(self.start_date, self.end_date),
							]
						),
					]
				)
			)
		else:
			query = query.where(
				shift.end_date.isnull()
				| ((self.start_date >= shift.start_date) & (self.start_date <= shift.end_date))
			)

		return query.run(as_dict=True)

	def throw_overlap_error(self, shift_details):
		shift_details = frappe._dict(shift_details)
		if shift_details.docstatus == 1 and shift_details.status == "Active":
			msg = _(
				"Employee {0} already has an active Shift {1}: {2} that overlaps within this period."
			).format(
				frappe.bold(self.employee),
				frappe.bold(shift_details.shift_type),
				get_link_to_form("Shift Assignment", shift_details.name),
			)
			frappe.throw(msg, title=_("Overlapping Shifts"), exc=OverlappingShiftError)


def has_overlapping_timings(shift_1: str, shift_2: str) -> bool:
	"""
	Accepts two shift types and checks whether their timings are overlapping
	"""
	curr_shift = frappe.db.get_value("Shift Type", shift_1, ["start_time", "end_time"], as_dict=True)
	overlapping_shift = frappe.db.get_value(
		"Shift Type", shift_2, ["start_time", "end_time"], as_dict=True
	)

	if (
		(
			curr_shift.start_time > overlapping_shift.start_time
			and curr_shift.start_time < overlapping_shift.end_time
		)
		or (
			curr_shift.end_time > overlapping_shift.start_time
			and curr_shift.end_time < overlapping_shift.end_time
		)
		or (
			curr_shift.start_time <= overlapping_shift.start_time
			and curr_shift.end_time >= overlapping_shift.end_time
		)
	):
		return True
	return False


@frappe.whitelist()
def get_events(start, end, filters=None):
	from frappe.desk.calendar import get_event_conditions

	employee = frappe.db.get_value(
		"Employee", {"user_id": frappe.session.user}, ["name", "company"], as_dict=True
	)
	if employee:
		employee, company = employee.name, employee.company
	else:
		employee = ""
		company = frappe.db.get_value("Global Defaults", None, "default_company")

	conditions = get_event_conditions("Shift Assignment", filters)
	events = add_assignments(start, end, conditions=conditions)
	return events


def add_assignments(start, end, conditions=None):
	events = []

	query = """select name, start_date, end_date, employee_name,
		employee, docstatus, shift_type
		from `tabShift Assignment` where
		(
			start_date >= %(start_date)s
			or end_date <=  %(end_date)s
			or (%(start_date)s between start_date and end_date and %(end_date)s between start_date and end_date)
		)
		and docstatus = 1"""
	if conditions:
		query += conditions

	records = frappe.db.sql(query, {"start_date": start, "end_date": end}, as_dict=True)
	shift_timing_map = get_shift_type_timing([d.shift_type for d in records])

	for d in records:
		daily_event_start = d.start_date
		daily_event_end = d.end_date if d.end_date else getdate()
		delta = timedelta(days=1)
		while daily_event_start <= daily_event_end:
			start_timing = (
				frappe.utils.get_datetime(daily_event_start) + shift_timing_map[d.shift_type]["start_time"]
			)
			end_timing = (
				frappe.utils.get_datetime(daily_event_start) + shift_timing_map[d.shift_type]["end_time"]
			)
			daily_event_start += delta
			e = {
				"name": d.name,
				"doctype": "Shift Assignment",
				"start_date": start_timing,
				"end_date": end_timing,
				"title": cstr(d.employee_name) + ": " + cstr(d.shift_type),
				"docstatus": d.docstatus,
				"allDay": 0,
			}
			if e not in events:
				events.append(e)

	return events


def get_shift_type_timing(shift_types):
	shift_timing_map = {}
	data = frappe.get_all(
		"Shift Type", filters={"name": ("IN", shift_types)}, fields=["name", "start_time", "end_time"]
	)

	for d in data:
		shift_timing_map[d.name] = d

	return shift_timing_map


def get_shift_for_time(shifts: List[Dict], for_timestamp: datetime) -> Dict:
	"""Returns shift with details for given timestamp"""
	valid_shifts = []

	for entry in shifts:
		shift_details = get_shift_details(entry.shift_type, for_timestamp=for_timestamp)

		if (
			get_datetime(shift_details.actual_start)
			<= get_datetime(for_timestamp)
			<= get_datetime(shift_details.actual_end)
		):
			valid_shifts.append(shift_details)

	valid_shifts.sort(key=lambda x: x["actual_start"])

	if len(valid_shifts) > 1:
		for i in range(len(valid_shifts) - 1):
			# comparing 2 consecutive shifts and adjusting start and end times
			# if they are overlapping within grace period
			curr_shift = valid_shifts[i]
			next_shift = valid_shifts[i + 1]

			if curr_shift and next_shift:
				next_shift.actual_start = (
					curr_shift.end_datetime
					if next_shift.actual_start < curr_shift.end_datetime
					else next_shift.actual_start
				)
				curr_shift.actual_end = (
					next_shift.actual_start
					if curr_shift.actual_end > next_shift.actual_start
					else curr_shift.actual_end
				)

			valid_shifts[i] = curr_shift
			valid_shifts[i + 1] = next_shift

		return get_exact_shift(valid_shifts, for_timestamp) or {}

	return (valid_shifts and valid_shifts[0]) or {}


def get_shifts_for_date(employee: str, for_timestamp: datetime) -> List[Dict[str, str]]:
	"""Returns list of shifts with details for given date"""
	assignment = frappe.qb.DocType("Shift Assignment")

	return (
		frappe.qb.from_(assignment)
		.select(assignment.name, assignment.shift_type)
		.where(
			(assignment.employee == employee)
			& (assignment.docstatus == 1)
			& (assignment.status == "Active")
			& (assignment.start_date <= getdate(for_timestamp.date()))
			& (
				Criterion.any(
					[
						assignment.end_date.isnull(),
						(assignment.end_date.isnotnull() & (getdate(for_timestamp.date()) <= assignment.end_date)),
					]
				)
			)
		)
	).run(as_dict=True)


def get_shift_for_timestamp(employee: str, for_timestamp: datetime) -> Dict:
	shifts = get_shifts_for_date(employee, for_timestamp)
	if shifts:
		return get_shift_for_time(shifts, for_timestamp)
	return {}


def get_employee_shift(
	employee: str,
	for_timestamp: datetime = None,
	consider_default_shift: bool = False,
	next_shift_direction: str = None,
) -> Dict:
	"""Returns a Shift Type for the given employee on the given date. (excluding the holidays)

	:param employee: Employee for which shift is required.
	:param for_timestamp: DateTime on which shift is required
	:param consider_default_shift: If set to true, default shift is taken when no shift assignment is found.
	:param next_shift_direction: One of: None, 'forward', 'reverse'. Direction to look for next shift if shift not found on given date.
	"""
	if for_timestamp is None:
		for_timestamp = now_datetime()

	shift_details = get_shift_for_timestamp(employee, for_timestamp)

	# if shift assignment is not found, consider default shift
	default_shift = frappe.db.get_value("Employee", employee, "default_shift")
	if not shift_details and consider_default_shift:
		shift_details = get_shift_details(default_shift, for_timestamp)

	# if its a holiday, reset
	if shift_details and is_holiday_date(employee, shift_details):
		shift_details = None

	# if no shift is found, find next or prev shift assignment based on direction
	if not shift_details and next_shift_direction:
		shift_details = get_prev_or_next_shift(
			employee, for_timestamp, consider_default_shift, default_shift, next_shift_direction
		)

	return shift_details or {}


def get_prev_or_next_shift(
	employee: str,
	for_timestamp: datetime,
	consider_default_shift: bool,
	default_shift: str,
	next_shift_direction: str,
) -> Dict:
	"""Returns a dict of shift details for the next or prev shift based on the next_shift_direction"""
	MAX_DAYS = 366
	shift_details = {}

	if consider_default_shift and default_shift:
		direction = -1 if next_shift_direction == "reverse" else 1
		for i in range(MAX_DAYS):
			date = for_timestamp + timedelta(days=direction * (i + 1))
			shift_details = get_employee_shift(employee, date, consider_default_shift, None)
			if shift_details:
				break
	else:
		direction = "<" if next_shift_direction == "reverse" else ">"
		sort_order = "desc" if next_shift_direction == "reverse" else "asc"
		dates = frappe.db.get_all(
			"Shift Assignment",
			["start_date", "end_date"],
			{
				"employee": employee,
				"start_date": (direction, for_timestamp.date()),
				"docstatus": 1,
				"status": "Active",
			},
			as_list=True,
			limit=MAX_DAYS,
			order_by="start_date " + sort_order,
		)

		if dates:
			for date in dates:
				if date[1] and date[1] < for_timestamp.date():
					continue
				shift_details = get_employee_shift(
					employee, datetime.combine(date[0], for_timestamp.time()), consider_default_shift, None
				)
				if shift_details:
					break

	return shift_details or {}


def is_holiday_date(employee: str, shift_details: Dict) -> bool:
	holiday_list_name = frappe.db.get_value(
		"Shift Type", shift_details.shift_type.name, "holiday_list"
	)

	if not holiday_list_name:
		holiday_list_name = get_holiday_list_for_employee(employee, False)

	return holiday_list_name and is_holiday(holiday_list_name, shift_details.start_datetime.date())


def get_employee_shift_timings(
	employee: str, for_timestamp: datetime = None, consider_default_shift: bool = False
) -> List[Dict]:
	"""Returns previous shift, current/upcoming shift, next_shift for the given timestamp and employee"""
	if for_timestamp is None:
		for_timestamp = now_datetime()

	# write and verify a test case for midnight shift.
	prev_shift = curr_shift = next_shift = None
	curr_shift = get_employee_shift(employee, for_timestamp, consider_default_shift, "forward")
	if curr_shift:
		next_shift = get_employee_shift(
			employee, curr_shift.start_datetime + timedelta(days=1), consider_default_shift, "forward"
		)
	prev_shift = get_employee_shift(
		employee, for_timestamp + timedelta(days=-1), consider_default_shift, "reverse"
	)

	if curr_shift:
		# adjust actual start and end times if they are overlapping with grace period (before start and after end)
		if prev_shift:
			curr_shift.actual_start = (
				prev_shift.end_datetime
				if curr_shift.actual_start < prev_shift.end_datetime
				else curr_shift.actual_start
			)
			prev_shift.actual_end = (
				curr_shift.actual_start
				if prev_shift.actual_end > curr_shift.actual_start
				else prev_shift.actual_end
			)
		if next_shift:
			next_shift.actual_start = (
				curr_shift.end_datetime
				if next_shift.actual_start < curr_shift.end_datetime
				else next_shift.actual_start
			)
			curr_shift.actual_end = (
				next_shift.actual_start
				if curr_shift.actual_end > next_shift.actual_start
				else curr_shift.actual_end
			)

	return prev_shift, curr_shift, next_shift


def get_actual_start_end_datetime_of_shift(
	employee: str, for_timestamp: datetime, consider_default_shift: bool = False
) -> Dict:
	"""Returns a Dict containing shift details with actual_start and actual_end datetime values
	Here 'actual' means taking into account the "begin_check_in_before_shift_start_time" and "allow_check_out_after_shift_end_time".
	Empty Dict is returned if the timestamp is outside any actual shift timings.

	:param employee (str): Employee name
	:param for_timestamp (datetime, optional): Datetime value of checkin, if not provided considers current datetime
	:param consider_default_shift (bool, optional): Flag (defaults to False) to specify whether to consider
	default shift in employee master if no shift assignment is found
	"""
	shift_timings_as_per_timestamp = get_employee_shift_timings(
		employee, for_timestamp, consider_default_shift
	)
	return get_exact_shift(shift_timings_as_per_timestamp, for_timestamp)


def get_exact_shift(shifts: List, for_timestamp: datetime) -> Dict:
	"""Returns the shift details (dict) for the exact shift in which the 'for_timestamp' value falls among multiple shifts"""
	shift_details = dict()
	timestamp_list = []

	for shift in shifts:
		if shift:
			timestamp_list.extend([shift.actual_start, shift.actual_end])
		else:
			timestamp_list.extend([None, None])

	timestamp_index = None
	for index, timestamp in enumerate(timestamp_list):
		if not timestamp:
			continue

		if for_timestamp < timestamp:
			timestamp_index = index
		elif for_timestamp == timestamp:
			# on timestamp boundary
			if index % 2 == 1:
				timestamp_index = index
			else:
				timestamp_index = index + 1

		if timestamp_index:
			break

	if timestamp_index and timestamp_index % 2 == 1:
		shift_details = shifts[int((timestamp_index - 1) / 2)]

	return shift_details


def get_shift_details(shift_type_name: str, for_timestamp: datetime = None) -> Dict:
	"""Returns a Dict containing shift details with the following data:
	'shift_type' - Object of DocType Shift Type,
	'start_datetime' - datetime of shift start on given timestamp,
	'end_datetime' - datetime of shift end on given timestamp,
	'actual_start' - datetime of shift start after adding 'begin_check_in_before_shift_start_time',
	'actual_end' - datetime of shift end after adding 'allow_check_out_after_shift_end_time' (None is returned if this is zero)

	:param shift_type_name (str): shift type name for which shift_details are required.
	:param for_timestamp (datetime, optional): Datetime value of checkin, if not provided considers current datetime
	"""
	if not shift_type_name:
		return {}

	if for_timestamp is None:
		for_timestamp = now_datetime()

	shift_type = frappe.get_doc("Shift Type", shift_type_name)
	shift_actual_start = shift_type.start_time - timedelta(
		minutes=shift_type.begin_check_in_before_shift_start_time
	)

	if shift_type.start_time > shift_type.end_time:
		# shift spans accross 2 different days
		if get_time(for_timestamp.time()) >= get_time(shift_actual_start):
			# if for_timestamp is greater than start time, it's within the first day
			start_datetime = datetime.combine(for_timestamp, datetime.min.time()) + shift_type.start_time
			for_timestamp = for_timestamp + timedelta(days=1)
			end_datetime = datetime.combine(for_timestamp, datetime.min.time()) + shift_type.end_time

		elif get_time(for_timestamp.time()) < get_time(shift_actual_start):
			# if for_timestamp is less than start time, it's within the second day
			end_datetime = datetime.combine(for_timestamp, datetime.min.time()) + shift_type.end_time
			for_timestamp = for_timestamp + timedelta(days=-1)
			start_datetime = datetime.combine(for_timestamp, datetime.min.time()) + shift_type.start_time
	else:
		# start and end timings fall on the same day
		start_datetime = datetime.combine(for_timestamp, datetime.min.time()) + shift_type.start_time
		end_datetime = datetime.combine(for_timestamp, datetime.min.time()) + shift_type.end_time

	actual_start = start_datetime - timedelta(
		minutes=shift_type.begin_check_in_before_shift_start_time
	)
	actual_end = end_datetime + timedelta(minutes=shift_type.allow_check_out_after_shift_end_time)

	return frappe._dict(
		{
			"shift_type": shift_type,
			"start_datetime": start_datetime,
			"end_datetime": end_datetime,
			"actual_start": actual_start,
			"actual_end": actual_end,
		}
	)
