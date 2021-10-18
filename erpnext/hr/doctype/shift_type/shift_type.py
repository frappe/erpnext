# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import itertools
from datetime import timedelta

import frappe
from frappe.model.document import Document
from frappe.utils import cint, get_datetime, getdate

from erpnext.hr.doctype.attendance.attendance import mark_attendance
from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee
from erpnext.hr.doctype.employee_checkin.employee_checkin import (
	calculate_working_hours,
	mark_attendance_and_link_log,
)
from erpnext.hr.doctype.shift_assignment.shift_assignment import (
	get_actual_start_end_datetime_of_shift,
	get_employee_shift,
)


class ShiftType(Document):
	@frappe.whitelist()
	def process_auto_attendance(self):
		if not cint(self.enable_auto_attendance) or not self.process_attendance_after or not self.last_sync_of_checkin:
			return
		filters = {
			'skip_auto_attendance':'0',
			'attendance':('is', 'not set'),
			'time':('>=', self.process_attendance_after),
			'shift_actual_end': ('<', self.last_sync_of_checkin),
			'shift': self.name
		}
		logs = frappe.db.get_list('Employee Checkin', fields="*", filters=filters, order_by="employee,time")
		for key, group in itertools.groupby(logs, key=lambda x: (x['employee'], x['shift_actual_start'])):
			single_shift_logs = list(group)
			attendance_status, working_hours, late_entry, early_exit, in_time, out_time = self.get_attendance(single_shift_logs)
			mark_attendance_and_link_log(single_shift_logs, attendance_status, key[1].date(), working_hours, late_entry, early_exit, in_time, out_time, self.name)
		for employee in self.get_assigned_employee(self.process_attendance_after, True):
			self.mark_absent_for_dates_with_no_attendance(employee)

	def get_attendance(self, logs):
		"""Return attendance_status, working_hours, late_entry, early_exit, in_time, out_time
		for a set of logs belonging to a single shift.
		Assumtion:
			1. These logs belongs to an single shift, single employee and is not in a holiday date.
			2. Logs are in chronological order
		"""
		late_entry = early_exit = False
		total_working_hours, in_time, out_time = calculate_working_hours(logs, self.determine_check_in_and_check_out, self.working_hours_calculation_based_on)
		if cint(self.enable_entry_grace_period) and in_time and in_time > logs[0].shift_start + timedelta(minutes=cint(self.late_entry_grace_period)):
			late_entry = True

		if cint(self.enable_exit_grace_period) and out_time and out_time < logs[0].shift_end - timedelta(minutes=cint(self.early_exit_grace_period)):
			early_exit = True

		if self.working_hours_threshold_for_absent and total_working_hours < self.working_hours_threshold_for_absent:
			return 'Absent', total_working_hours, late_entry, early_exit, in_time, out_time
		if self.working_hours_threshold_for_half_day and total_working_hours < self.working_hours_threshold_for_half_day:
			return 'Half Day', total_working_hours, late_entry, early_exit, in_time, out_time
		return 'Present', total_working_hours, late_entry, early_exit, in_time, out_time

	def mark_absent_for_dates_with_no_attendance(self, employee):
		"""Marks Absents for the given employee on working days in this shift which have no attendance marked.
		The Absent is marked starting from 'process_attendance_after' or employee creation date.
		"""
		date_of_joining, relieving_date, employee_creation = frappe.db.get_value("Employee", employee, ["date_of_joining", "relieving_date", "creation"])
		if not date_of_joining:
			date_of_joining = employee_creation.date()
		start_date = max(getdate(self.process_attendance_after), date_of_joining)
		actual_shift_datetime = get_actual_start_end_datetime_of_shift(employee, get_datetime(self.last_sync_of_checkin), True)
		last_shift_time = actual_shift_datetime[0] if actual_shift_datetime[0] else get_datetime(self.last_sync_of_checkin)
		prev_shift = get_employee_shift(employee, last_shift_time.date()-timedelta(days=1), True, 'reverse')
		if prev_shift:
			end_date = min(prev_shift.start_datetime.date(), relieving_date) if relieving_date else prev_shift.start_datetime.date()
		else:
			return
		holiday_list_name = self.holiday_list
		if not holiday_list_name:
			holiday_list_name = get_holiday_list_for_employee(employee, False)
		dates = get_filtered_date_list(employee, start_date, end_date, holiday_list=holiday_list_name)
		for date in dates:
			shift_details = get_employee_shift(employee, date, True)
			if shift_details and shift_details.shift_type.name == self.name:
				mark_attendance(employee, date, 'Absent', self.name)

	def get_assigned_employee(self, from_date=None, consider_default_shift=False):
		filters = {'start_date':('>', from_date), 'shift_type': self.name, 'docstatus': '1'}
		if not from_date:
			del filters["start_date"]

		assigned_employees = frappe.get_all('Shift Assignment', 'employee', filters, as_list=True)
		assigned_employees = [x[0] for x in assigned_employees]

		if consider_default_shift:
			filters = {'default_shift': self.name, 'status': ['!=', 'Inactive']}
			default_shift_employees = frappe.get_all('Employee', 'name', filters, as_list=True)
			default_shift_employees = [x[0] for x in default_shift_employees]
			return list(set(assigned_employees+default_shift_employees))
		return assigned_employees

def process_auto_attendance_for_all_shifts():
	shift_list = frappe.get_all('Shift Type', 'name', {'enable_auto_attendance':'1'}, as_list=True)
	for shift in shift_list:
		doc = frappe.get_doc('Shift Type', shift[0])
		doc.process_auto_attendance()

def get_filtered_date_list(employee, start_date, end_date, filter_attendance=True, holiday_list=None):
	"""Returns a list of dates after removing the dates with attendance and holidays
	"""
	base_dates_query = """select adddate(%(start_date)s, t2.i*100 + t1.i*10 + t0.i) selected_date from
		(select 0 i union select 1 union select 2 union select 3 union select 4 union select 5 union select 6 union select 7 union select 8 union select 9) t0,
		(select 0 i union select 1 union select 2 union select 3 union select 4 union select 5 union select 6 union select 7 union select 8 union select 9) t1,
		(select 0 i union select 1 union select 2 union select 3 union select 4 union select 5 union select 6 union select 7 union select 8 union select 9) t2"""
	condition_query = ''
	if filter_attendance:
		condition_query += """ and a.selected_date not in (
			select attendance_date from `tabAttendance`
			where docstatus = 1 and employee = %(employee)s
			and attendance_date between %(start_date)s and %(end_date)s)"""
	if holiday_list:
		condition_query += """ and a.selected_date not in (
			select holiday_date from `tabHoliday` where parenttype = 'Holiday List' and
    		parentfield = 'holidays' and parent = %(holiday_list)s
    		and holiday_date between %(start_date)s and %(end_date)s)"""

	dates = frappe.db.sql("""select * from
		({base_dates_query}) as a
		where a.selected_date <= %(end_date)s {condition_query}
		""".format(base_dates_query=base_dates_query, condition_query=condition_query),
		{"employee":employee, "start_date":start_date, "end_date":end_date, "holiday_list":holiday_list}, as_list=True)

	return [getdate(date[0]) for date in dates]
