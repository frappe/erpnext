# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, cstr, date_diff, flt, formatdate, getdate, now_datetime, nowdate
from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee
from erpnext.hr.doctype.holiday_list.holiday_list import is_holiday
from datetime import timedelta, datetime

class OverlapError(frappe.ValidationError): pass

class ShiftAssignment(Document):
	def validate(self):
		self.validate_overlapping_dates()

	def validate_overlapping_dates(self):
			if not self.name:
				self.name = "New Shift Assignment"

			d = frappe.db.sql("""
				select
					name, shift_type, date
				from `tabShift Assignment`
				where employee = %(employee)s and docstatus < 2
				and date = %(date)s
				and name != %(name)s""", {
					"employee": self.employee,
					"shift_type": self.shift_type,
					"date": self.date,
					"name": self.name
				}, as_dict = 1)

			for date_overlap in d:
				if date_overlap['name']:
					self.throw_overlap_error(date_overlap)

	def throw_overlap_error(self, d):
		msg = _("Employee {0} has already applied for {1} on {2} : ").format(self.employee,
			d['shift_type'], formatdate(d['date'])) \
			+ """ <b><a href="#Form/Shift Assignment/{0}">{0}</a></b>""".format(d["name"])
		frappe.throw(msg, OverlapError)

@frappe.whitelist()
def get_events(start, end, filters=None):
	events = []

	employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, ["name", "company"],
		as_dict=True)
	if employee:
		employee, company = employee.name, employee.company
	else:
		employee=''
		company=frappe.db.get_value("Global Defaults", None, "default_company")

	from frappe.desk.reportview import get_filters_cond
	conditions = get_filters_cond("Shift Assignment", filters, [])
	add_assignments(events, start, end, conditions=conditions)
	return events

def add_assignments(events, start, end, conditions=None):
	query = """select name, date, employee_name, 
		employee, docstatus
		from `tabShift Assignment` where
		date <= %(date)s
		and docstatus < 2"""
	if conditions:
		query += conditions

	for d in frappe.db.sql(query, {"date":start, "date":end}, as_dict=True):
		e = {
			"name": d.name,
			"doctype": "Shift Assignment",
			"date": d.date,
			"title": cstr(d.employee_name) + \
				cstr(d.shift_type),
			"docstatus": d.docstatus
		}
		if e not in events:
			events.append(e)


def get_employee_shift(employee, for_date=nowdate(), consider_default_shift=False, next_shift_direction=None):
	"""Returns a Shift Type for the given employee on the given date. (excluding the holidays)

	:param employee: Employee for which shift is required.
	:param for_date: Date on which shift are required
	:param consider_default_shift: If set to true, default shift is taken when no shift assignment is found.
	:param next_shift_direction: One of: None, 'forward', 'reverse'. Direction to look for next shift if shift not found on given date.
	"""
	default_shift = frappe.db.get_value('Employee', employee, 'default_shift')
	shift_type_name = frappe.db.get_value('Shift Assignment', {'employee':employee, 'date': for_date, 'docstatus': '1'}, 'shift_type')
	if not shift_type_name and consider_default_shift:
		shift_type_name = default_shift
	if shift_type_name:
		holiday_list_name = frappe.db.get_value('Shift Type', shift_type_name, 'holiday_list')
		if not holiday_list_name:
			holiday_list_name = get_holiday_list_for_employee(employee, False)
		if holiday_list_name and is_holiday(holiday_list_name, for_date):
			shift_type_name = None

	if not shift_type_name and next_shift_direction:
		MAX_DAYS = 366
		if consider_default_shift and default_shift:
			direction = -1 if next_shift_direction == 'reverse' else +1
			for i in range(MAX_DAYS):
				date = for_date+timedelta(days=direction*(i+1))
				shift_details = get_employee_shift(employee, date, consider_default_shift, None)
				if shift_details:
					shift_type_name = shift_details.shift_type.name
					for_date = date
					break
		else:
			direction = '<' if next_shift_direction == 'reverse' else '>'
			sort_order = 'desc' if next_shift_direction == 'reverse' else 'asc'
			dates = frappe.db.get_all('Shift Assignment',
				'date',
				{'employee':employee, 'date':(direction, for_date), 'docstatus': '1'},
				as_list=True,
				limit=MAX_DAYS, order_by="date "+sort_order)
			for date in dates:
				shift_details = get_employee_shift(employee, date[0], consider_default_shift, None)
				if shift_details:
					shift_type_name = shift_details.shift_type.name
					for_date = date[0]
					break

	return get_shift_details(shift_type_name, for_date)


def get_employee_shift_timings(employee, for_timestamp=now_datetime(), consider_default_shift=False):
	"""Returns previous shift, current/upcoming shift, next_shift for the given timestamp and employee
	"""
	# write and verify a test case for midnight shift. 
	prev_shift = curr_shift = next_shift = None
	curr_shift = get_employee_shift(employee, for_timestamp.date(), consider_default_shift, 'forward')
	if curr_shift:
		next_shift = get_employee_shift(employee, curr_shift.start_datetime.date()+timedelta(days=1), consider_default_shift, 'forward')
	prev_shift = get_employee_shift(employee, for_timestamp.date()+timedelta(days=-1), consider_default_shift, 'reverse')

	if curr_shift:
		if prev_shift:
			curr_shift.actual_start = prev_shift.end_datetime if curr_shift.actual_start < prev_shift.end_datetime else curr_shift.actual_start
			prev_shift.actual_end = curr_shift.actual_start if prev_shift.actual_end > curr_shift.actual_start else prev_shift.actual_end
		if next_shift:
			next_shift.actual_start = curr_shift.end_datetime if next_shift.actual_start < curr_shift.end_datetime else next_shift.actual_start
			curr_shift.actual_end = next_shift.actual_start if curr_shift.actual_end > next_shift.actual_start else curr_shift.actual_end
	return prev_shift, curr_shift, next_shift


def get_shift_details(shift_type_name, for_date=nowdate()):
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
	shift_type = frappe.get_doc('Shift Type', shift_type_name)
	start_datetime = datetime.combine(for_date, datetime.min.time()) + shift_type.start_time
	for_date = for_date + timedelta(days=1) if shift_type.start_time > shift_type.end_time else for_date
	end_datetime = datetime.combine(for_date, datetime.min.time()) + shift_type.end_time
	actual_start = start_datetime - timedelta(minutes=shift_type.begin_check_in_before_shift_start_time)
	actual_end = end_datetime + timedelta(minutes=shift_type.allow_check_out_after_shift_end_time)

	return frappe._dict({
		'shift_type': shift_type,
		'start_datetime': start_datetime,
		'end_datetime': end_datetime,
		'actual_start': actual_start,
		'actual_end': actual_end
	})


def get_actual_start_end_datetime_of_shift(employee, for_datetime, consider_default_shift=False):
	"""Takes a datetime and returns the 'actual' start datetime and end datetime of the shift in which the timestamp belongs.
		Here 'actual' means - taking in to account the "begin_check_in_before_shift_start_time" and "allow_check_out_after_shift_end_time".
		None is returned if the timestamp is outside any actual shift timings.
		Shift Details is also returned(current/upcoming i.e. if timestamp not in any actual shift then details of next shift returned)
	"""
	actual_shift_start = actual_shift_end = shift_details = None
	shift_timings_as_per_timestamp = get_employee_shift_timings(employee, for_datetime, consider_default_shift)
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
	if timestamp_index and timestamp_index%2 == 1:
		shift_details = shift_timings_as_per_timestamp[int((timestamp_index-1)/2)]
		actual_shift_start = shift_details.actual_start
		actual_shift_end = shift_details.actual_end
	elif timestamp_index:
		shift_details = shift_timings_as_per_timestamp[int(timestamp_index/2)]

	return actual_shift_start, actual_shift_end, shift_details
