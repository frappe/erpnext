# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, getdate, now_datetime, nowdate

from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee
from erpnext.hr.doctype.holiday_list.holiday_list import is_holiday
from erpnext.hr.utils import validate_active_employee


class ShiftAssignment(Document):
	def validate(self):
		validate_active_employee(self.employee)
		self.validate_overlapping_dates()

		if self.end_date:
			self.validate_from_to_dates("start_date", "end_date")

	def validate_overlapping_dates(self):
		if not self.name:
			self.name = "New Shift Assignment"

		condition = """and (
				end_date is null
				or
					%(start_date)s between start_date and end_date
		"""

		if self.end_date:
			condition += """ or
					%(end_date)s between start_date and end_date
					or
					start_date between %(start_date)s and %(end_date)s
				) """
		else:
			condition += """ ) """

		assigned_shifts = frappe.db.sql(
			"""
			select name, shift_type, start_date ,end_date, docstatus, status
			from `tabShift Assignment`
			where
				employee=%(employee)s and docstatus = 1
				and name != %(name)s
				and status = "Active"
				{0}
		""".format(
				condition
			),
			{
				"employee": self.employee,
				"shift_type": self.shift_type,
				"start_date": self.start_date,
				"end_date": self.end_date,
				"name": self.name,
			},
			as_dict=1,
		)

		if len(assigned_shifts):
			self.throw_overlap_error(assigned_shifts[0])

	def throw_overlap_error(self, shift_details):
		shift_details = frappe._dict(shift_details)
		if shift_details.docstatus == 1 and shift_details.status == "Active":
			msg = _("Employee {0} already has Active Shift {1}: {2}").format(
				frappe.bold(self.employee), frappe.bold(self.shift_type), frappe.bold(shift_details.name)
			)
		if shift_details.start_date:
			msg += _(" from {0}").format(getdate(self.start_date).strftime("%d-%m-%Y"))
			title = "Ongoing Shift"
			if shift_details.end_date:
				msg += _(" to {0}").format(getdate(self.end_date).strftime("%d-%m-%Y"))
				title = "Active Shift"
		if msg:
			frappe.throw(msg, title=title)


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


def get_employee_shift(
	employee, for_date=None, consider_default_shift=False, next_shift_direction=None
):
	"""Returns a Shift Type for the given employee on the given date. (excluding the holidays)

	:param employee: Employee for which shift is required.
	:param for_date: Date on which shift are required
	:param consider_default_shift: If set to true, default shift is taken when no shift assignment is found.
	:param next_shift_direction: One of: None, 'forward', 'reverse'. Direction to look for next shift if shift not found on given date.
	"""
	if for_date is None:
		for_date = nowdate()
	default_shift = frappe.get_cached_value("Employee", employee, "default_shift")
	shift_type_name = None
	shift_assignment_details = frappe.db.get_value(
		"Shift Assignment",
		{"employee": employee, "start_date": ("<=", for_date), "docstatus": "1", "status": "Active"},
		["shift_type", "end_date"],
	)

	if shift_assignment_details:
		shift_type_name = shift_assignment_details[0]

		# if end_date present means that shift is over after end_date else it is a ongoing shift.
		if shift_assignment_details[1] and for_date >= shift_assignment_details[1]:
			shift_type_name = None

	if not shift_type_name and consider_default_shift:
		shift_type_name = default_shift
	if shift_type_name:
		holiday_list_name = frappe.get_cached_value("Shift Type", shift_type_name, "holiday_list")
		if not holiday_list_name:
			holiday_list_name = get_holiday_list_for_employee(employee, False)
		if holiday_list_name and is_holiday(holiday_list_name, for_date):
			shift_type_name = None

	if not shift_type_name and next_shift_direction:
		MAX_DAYS = 366
		if consider_default_shift and default_shift:
			direction = -1 if next_shift_direction == "reverse" else +1
			for i in range(MAX_DAYS):
				date = for_date + timedelta(days=direction * (i + 1))
				shift_details = get_employee_shift(employee, date, consider_default_shift, None)
				if shift_details:
					shift_type_name = shift_details.shift_type.name
					for_date = date
					break
		else:
			direction = "<" if next_shift_direction == "reverse" else ">"
			sort_order = "desc" if next_shift_direction == "reverse" else "asc"
			dates = frappe.db.get_all(
				"Shift Assignment",
				["start_date", "end_date"],
				{
					"employee": employee,
					"start_date": (direction, for_date),
					"docstatus": "1",
					"status": "Active",
				},
				as_list=True,
				limit=MAX_DAYS,
				order_by="start_date " + sort_order,
			)

			if dates:
				for date in dates:
					if date[1] and date[1] < for_date:
						continue
					shift_details = get_employee_shift(employee, date[0], consider_default_shift, None)
					if shift_details:
						shift_type_name = shift_details.shift_type.name
						for_date = date[0]
						break

	return get_shift_details(shift_type_name, for_date)


def get_employee_shift_timings(employee, for_timestamp=None, consider_default_shift=False):
	"""Returns previous shift, current/upcoming shift, next_shift for the given timestamp and employee"""
	if for_timestamp is None:
		for_timestamp = now_datetime()
	# write and verify a test case for midnight shift.
	prev_shift = curr_shift = next_shift = None
	curr_shift = get_employee_shift(employee, for_timestamp.date(), consider_default_shift, "forward")
	if curr_shift:
		next_shift = get_employee_shift(
			employee,
			curr_shift.start_datetime.date() + timedelta(days=1),
			consider_default_shift,
			"forward",
		)
	prev_shift = get_employee_shift(
		employee, for_timestamp.date() + timedelta(days=-1), consider_default_shift, "reverse"
	)

	if curr_shift:
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


def get_shift_details(shift_type_name, for_date=None):
	"""Returns Shift Details which contain some additional information as described below.
	'shift_details' contains the following keys:
	        'shift_type' - Object of DocType Shift Type,
	        'start_datetime' - Date and Time of shift start on given date,
	        'end_datetime' - Date and Time of shift end on given date,
	        'actual_start' - datetime of shift start after adding 'begin_check_in_before_shift_start_time',
	        'actual_end' - datetime of shift end after adding 'allow_check_out_after_shift_end_time'(None is returned if this is zero)

	:param shift_type_name: shift type name for which shift_details is required.
	:param for_date: Date on which shift_details are required
	"""
	if not shift_type_name:
		return None
	if not for_date:
		for_date = nowdate()
	shift_type = frappe.get_cached_value(
		"Shift Type",
		shift_type_name,
		[
			"name",
			"start_time",
			"end_time",
			"begin_check_in_before_shift_start_time",
			"allow_check_out_after_shift_end_time",
		],
		as_dict=1,
	)
	start_datetime = datetime.combine(for_date, datetime.min.time()) + shift_type.start_time
	for_date = (
		for_date + timedelta(days=1) if shift_type.start_time > shift_type.end_time else for_date
	)
	end_datetime = datetime.combine(for_date, datetime.min.time()) + shift_type.end_time
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


def get_actual_start_end_datetime_of_shift(employee, for_datetime, consider_default_shift=False):
	"""Takes a datetime and returns the 'actual' start datetime and end datetime of the shift in which the timestamp belongs.
	Here 'actual' means - taking in to account the "begin_check_in_before_shift_start_time" and "allow_check_out_after_shift_end_time".
	None is returned if the timestamp is outside any actual shift timings.
	Shift Details is also returned(current/upcoming i.e. if timestamp not in any actual shift then details of next shift returned)
	"""
	actual_shift_start = actual_shift_end = shift_details = None
	shift_timings_as_per_timestamp = get_employee_shift_timings(
		employee, for_datetime, consider_default_shift
	)
	timestamp_list = []
	for shift in shift_timings_as_per_timestamp:
		if shift:
			timestamp_list.extend([shift.actual_start, shift.actual_end])
		else:
			timestamp_list.extend([None, None])
	timestamp_index = None
	for index, timestamp in enumerate(timestamp_list):
		if timestamp and for_datetime <= timestamp:
			timestamp_index = index
			break
	if timestamp_index and timestamp_index % 2 == 1:
		shift_details = shift_timings_as_per_timestamp[int((timestamp_index - 1) / 2)]
		actual_shift_start = shift_details.actual_start
		actual_shift_end = shift_details.actual_end
	elif timestamp_index:
		shift_details = shift_timings_as_per_timestamp[int(timestamp_index / 2)]

	return actual_shift_start, actual_shift_end, shift_details
