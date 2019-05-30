# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import get_datetime, getdate
from datetime import timedelta
from frappe import _

from frappe.model.document import Document
from erpnext.hr.doctype.shift_assignment.shift_assignment import get_employee_shift_timings, get_employee_shift
from erpnext.hr.doctype.employee_attendance_log.employee_attendance_log import mark_attendance_and_link_log
from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee
from erpnext.hr.doctype.attendance.attendance import mark_absent

class HRSettings(Document):
	def validate(self):
		self.set_naming_series()
		self.validate_password_policy()

	def set_naming_series(self):
		from erpnext.setup.doctype.naming_series.naming_series import set_by_naming_series
		set_by_naming_series("Employee", "employee_number",
			self.get("emp_created_by")=="Naming Series", hide_name_field=True)

	def validate_password_policy(self):
		if self.email_salary_slip_to_employee and self.encrypt_salary_slips_in_emails:
			if not self.password_policy:
				frappe.throw(_("Password policy for Salary Slips is not set"))


def make_attendance_from_employee_attendance_log():
	hr_settings = frappe.db.get_singles_dict("HR Settings")
	if hr_settings.disable_auto_attendance == '1' or not hr_settings.process_attendance_after:
		return

	frappe.flags.hr_settings_for_auto_attendance = hr_settings
	filters = {'skip_auto_attendance':'0', 'attendance_marked':('is', 'not set'), 'time':('>=', hr_settings.process_attendance_after)}

	logs = frappe.db.get_all('Employee Attendance Log', fields="*", filters=filters, order_by="employee,time")
	single_employee_logs = []
	for log in logs:
		if not len(single_employee_logs) or (len(single_employee_logs) and single_employee_logs[0].employee == log.employee):
			single_employee_logs.append(log)
		else:
			process_single_employee_logs(single_employee_logs, hr_settings)
			single_employee_logs = [log]
	process_single_employee_logs(single_employee_logs, hr_settings)

def process_single_employee_logs(logs, hr_settings=None):
	"""Takes logs of a single employee in chronological order and tries to mark attendance for that employee.
	"""
	last_log = logs[-1]
	if not hr_settings:
		hr_settings = frappe.db.get_singles_dict("HR Settings")
	consider_default_shift = bool(hr_settings.attendance_for_employee_without_shift == 'Based on Default Shift')
	employee_last_sync = get_employee_attendance_log_last_sync(last_log.employee, hr_settings, last_log)
	while logs:
		actual_shift_start, actual_shift_end, shift_details = get_actual_start_end_datetime_of_shift(logs[0].employee, logs[0].time, consider_default_shift)
		if actual_shift_end and actual_shift_end >= employee_last_sync:
			break # skip processing employee if last_sync timestamp is in the middle of a shift
		if not actual_shift_start and not actual_shift_end: # when the log does not belong to any 'actual' shift timings
			if not shift_details: # employee does not have any future shifts assigned
				if hr_settings.attendance_for_employee_without_shift == 'At least one Employee Attendance Log per day as present':
					single_day_logs = [logs.pop(0)]
					while logs and logs[0].time.date() == single_day_logs[0].time.date():
						single_day_logs.append(logs.pop(0))
					mark_attendance_and_link_log(single_day_logs, 'Present', single_day_logs[0].time.date())
					continue
				else:
					mark_attendance_and_link_log(logs, 'Skip', None) # skipping attendance for all logs
					break
			else:
				mark_attendance_and_link_log([logs.pop(0)], 'Skip', None) # skipping single log
				continue
		single_shift_logs = [logs.pop(0)]
		while logs and logs[0].time <= actual_shift_end:
			single_shift_logs.append(logs.pop(0))
		process_single_employee_shift_logs(single_shift_logs, shift_details)
	mark_absent_for_dates_with_no_attendance(last_log.employee, employee_last_sync, hr_settings)

def mark_absent_for_dates_with_no_attendance(employee, employee_last_sync, hr_settings=None):
	"""Marks Absents for the given employee on working days which have no attendance marked. 
	The Absent is marked starting from one shift before the employee_last_sync 
	going back to 'hr_settings.process_attendance_after' or employee creation date.
	"""
	if not hr_settings:
		hr_settings = frappe.db.get_singles_dict("HR Settings")
	consider_default_shift = bool(hr_settings.attendance_for_employee_without_shift == 'Based on Default Shift')
	employee_date_of_joining = frappe.db.get_value('Employee', employee, 'date_of_joining')
	if not employee_date_of_joining:
		employee_date_of_joining = frappe.db.get_value('Employee', employee, 'creation').date()
	start_date = max(getdate(hr_settings.process_attendance_after), employee_date_of_joining)

	actual_shift_datetime = get_actual_start_end_datetime_of_shift(employee, employee_last_sync, consider_default_shift)
	last_shift_time = actual_shift_datetime[0] if actual_shift_datetime[0] else employee_last_sync
	prev_shift = get_employee_shift(employee, last_shift_time.date()-timedelta(days=1), consider_default_shift, 'reverse')
	if prev_shift:
		end_date = prev_shift.start_datetime.date()
	elif hr_settings.attendance_for_employee_without_shift == 'At least one Employee Attendance Log per day as present':
		for date in get_filtered_date_list(employee, "All Dates", start_date, employee_last_sync.date(), True, get_holiday_list_for_employee(employee, False)):
			mark_absent(employee, date)
		return
	else:
		return

	if consider_default_shift:
		for date in get_filtered_date_list(employee, "All Dates", start_date, end_date):
			if get_employee_shift(employee, date, consider_default_shift):
				mark_absent(employee, date)
	elif hr_settings.attendance_for_employee_without_shift == 'At least one Employee Attendance Log per day as present':
		for date in get_filtered_date_list(employee, "All Dates", start_date, employee_last_sync.date(), True, get_holiday_list_for_employee(employee, False)):
			mark_absent(employee, date)
	else:
		for date in get_filtered_date_list(employee, "Assigned Shifts", start_date, end_date):
			if get_employee_shift(employee, date, consider_default_shift):
				mark_absent(employee, date)


def get_filtered_date_list(employee, base_dates_set, start_date, end_date, filter_attendance=True, holiday_list=None):
	"""
	:param base_dates_set: One of: "All Dates", "Assigned Shifts"
	"""
	if base_dates_set == "All Dates":
		base_dates_query = """select adddate(%(start_date)s, t2.i*100 + t1.i*10 + t0.i) selected_date from
			(select 0 i union select 1 union select 2 union select 3 union select 4 union select 5 union select 6 union select 7 union select 8 union select 9) t0,
			(select 0 i union select 1 union select 2 union select 3 union select 4 union select 5 union select 6 union select 7 union select 8 union select 9) t1,
			(select 0 i union select 1 union select 2 union select 3 union select 4 union select 5 union select 6 union select 7 union select 8 union select 9) t2"""
	else:
		base_dates_query = "select date as selected_date from `tabShift Assignment` where docstatus = '1' and employee = %(employee)s and date >= %(start_date)s"

	condition_query = ''
	if filter_attendance:
		condition_query += """and a.selected_date not in (
			select attendance_date from `tabAttendance` 
			where docstatus = '1' and employee = %(employee)s 
			and attendance_date between %(start_date)s and %(end_date)s)"""
	if holiday_list:
		condition_query += """and a.selected_date not in (
			select holiday_date from `tabHoliday` where parenttype = 'Holiday List' and
    		parentfield = 'holidays' and parent = %(holiday_list)s
    		and holiday_date between %(start_date)s and %(end_date)s)"""
	
	dates = frappe.db.sql("""select * from
		({base_dates_query}) as a
		where a.selected_date <= %(end_date)s {condition_query}
		""".format(base_dates_query=base_dates_query,condition_query=condition_query),
		{"employee":employee, "start_date":start_date, "end_date":end_date, "holiday_list":holiday_list},as_list=True)

	return [getdate(date[0]) for date in dates]


def process_single_employee_shift_logs(logs, shift_details):
	"""Mark Attendance for a set of logs belonging to a single shift.
	Assumtion: 
		1. These logs belongs to an single shift, single employee and is not in a holiday date.
		2. Logs are in chronological order
	"""
	if shift_details.shift_type.enable_auto_attendance:
		mark_attendance_and_link_log(logs, 'Skip', None)
		return
	check_in_out_type = shift_details.shift_type.determine_check_in_and_check_out
	working_hours_calc_type = shift_details.shift_type.working_hours_calculation_based_on
	total_working_hours = calculate_working_hours(logs, check_in_out_type, working_hours_calc_type)
	if shift_details.working_hours_threshold_for_absent and total_working_hours < shift_details.working_hours_threshold_for_absent:
		mark_attendance_and_link_log(logs, 'Absent', shift_details.start_datetime.date(), total_working_hours)
		return
	if shift_details.working_hours_threshold_for_half_day and total_working_hours < shift_details.working_hours_threshold_for_half_day:
		mark_attendance_and_link_log(logs, 'Half Day', shift_details.start_datetime.date(), total_working_hours)
		return
	mark_attendance_and_link_log(logs, 'Present', shift_details.start_datetime.date(), total_working_hours)


def calculate_working_hours(logs, check_in_out_type, working_hours_calc_type):
	"""Given a set of logs in chronological order calculates the total working hours based on the parameters.
	Zero is returned for all invalid cases.
	
	:param logs: The List of 'Employee Attendance Log'.
	:param check_in_out_type: One of: 'Alternating entries as IN and OUT during the same shift', 'Strictly based on Log Type in Employee Attendance Log'
	:param working_hours_calc_type: One of: 'First Check-in and Last Check-out', 'Every Valid Check-in and Check-out'
	"""
	total_hours = 0
	if check_in_out_type == 'Alternating entries as IN and OUT during the same shift':
		if working_hours_calc_type == 'First Check-in and Last Check-out':
			# assumption in this case: First log always IN, Last log always OUT
			total_hours = time_diff_in_hours(logs[0].time, logs[-1].time)
		elif working_hours_calc_type == 'Every Valid Check-in and Check-out':
			while len(logs) >= 2:
				total_hours += time_diff_in_hours(logs[0].time, logs[1].time)
				del logs[:2]

	elif check_in_out_type == 'Strictly based on Log Type in Employee Attendance Log':
		if working_hours_calc_type == 'First Check-in and Last Check-out':
			first_in_log = logs[find_index_in_dict(logs, 'log_type', 'IN')]
			last_out_log = logs[len(logs)-1-find_index_in_dict(reversed(logs), 'log_type', 'OUT')]
			if first_in_log and last_out_log:
				total_hours = time_diff_in_hours(first_in_log.time, last_out_log.time)
		elif working_hours_calc_type == 'Every Valid Check-in and Check-out':
			in_log = out_log = None
			for log in logs:
				if in_log and out_log:
					total_hours += time_diff_in_hours(in_log.time, out_log.time)
					in_log = out_log = None
				if not in_log:
					in_log = log if log.log_type == 'IN'  else None
				elif not out_log:
					out_log = log if log.log_type == 'OUT'  else None
			if in_log and out_log:
				total_hours += time_diff_in_hours(in_log.time, out_log.time)
	return total_hours


def time_diff_in_hours(start, end):
	return round((end-start).total_seconds() / 3600, 1)

def find_index_in_dict(dict_list, key, value):
	return next((index for (index, d) in enumerate(dict_list) if d[key] == value), None)

def get_actual_start_end_datetime_of_shift(employee, for_datetime, consider_default_shift=False):
	"""Takes a datetime and returns the 'actual' start datetime and end datetime of the shift in which the timestamp belongs.
		Here 'actual' means - taking in to account the "begin_check_in_before_shift_start_time" and "allow_check_out_after_shift_end_time".
		None is returned if the timestamp is outside any actual shift timings.
		Shift Details is also returned(current/upcoming i.e. if timestamp not in any actual shift then details of next shift returned)
	"""
	actual_shift_start = actual_shift_end = shift_details = None
	shift_timings_as_per_timestamp = get_employee_shift_timings(employee, for_datetime, consider_default_shift)
	prev_shift, curr_shift, next_shift = shift_timings_as_per_timestamp
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


def get_employee_attendance_log_last_sync(employee, hr_settings=None, last_log=None):
	"""This functions returns a last sync timestamp for the given employee.
	"""
	# when using inside auto attendance function 'last_log', 'hr_setting' is passed along
	if last_log:
		last_log_time = [last_log]
	else:
		last_log_time = frappe.db.get_all('Employee Attendance Log', fields="time", filters={'employee':employee}, limit=1, order_by='time desc')
	if not hr_settings:
		hr_settings = frappe.db.get_singles_dict("HR Settings")

	if last_log_time and hr_settings.last_sync_of_attendance_log:
		return max(last_log_time[0].time, get_datetime(hr_settings.last_sync_of_attendance_log))
	elif last_log_time:
		return last_log_time[0].time
	return get_datetime(hr_settings.last_sync_of_attendance_log) if hr_settings.last_sync_of_attendance_log else None
