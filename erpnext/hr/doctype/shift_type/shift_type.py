# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import itertools
from datetime import datetime, timedelta

import frappe
from frappe.model.document import Document
from frappe.utils import cint, get_datetime, get_time, getdate

from erpnext.buying.doctype.supplier_scorecard.supplier_scorecard import daterange
from erpnext.hr.doctype.attendance.attendance import mark_attendance
from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee
from erpnext.hr.doctype.employee_checkin.employee_checkin import (
	calculate_working_hours,
	mark_attendance_and_link_log,
)
from erpnext.hr.doctype.holiday_list.holiday_list import is_holiday
from erpnext.hr.doctype.shift_assignment.shift_assignment import (
	get_employee_shift,
	get_shift_details,
)


class ShiftType(Document):
	@frappe.whitelist()
	def process_auto_attendance(self):
		if (
			not cint(self.enable_auto_attendance)
			or not self.process_attendance_after
			or not self.last_sync_of_checkin
		):
			return

		filters = {
			"skip_auto_attendance": 0,
			"attendance": ("is", "not set"),
			"time": (">=", self.process_attendance_after),
			"shift_actual_end": ("<", self.last_sync_of_checkin),
			"shift": self.name,
		}
		logs = frappe.db.get_list(
			"Employee Checkin", fields="*", filters=filters, order_by="employee,time"
		)

		for key, group in itertools.groupby(
			logs, key=lambda x: (x["employee"], x["shift_actual_start"])
		):
			single_shift_logs = list(group)
			(
				attendance_status,
				working_hours,
				late_entry,
				early_exit,
				in_time,
				out_time,
			) = self.get_attendance(single_shift_logs)

			mark_attendance_and_link_log(
				single_shift_logs,
				attendance_status,
				key[1].date(),
				working_hours,
				late_entry,
				early_exit,
				in_time,
				out_time,
				self.name,
			)

		for employee in self.get_assigned_employee(self.process_attendance_after, True):
			self.mark_absent_for_dates_with_no_attendance(employee)

	def get_attendance(self, logs):
		"""Return attendance_status, working_hours, late_entry, early_exit, in_time, out_time
		for a set of logs belonging to a single shift.
		Assumptions:
		1. These logs belongs to a single shift, single employee and it's not in a holiday date.
		2. Logs are in chronological order
		"""
		late_entry = early_exit = False
		total_working_hours, in_time, out_time = calculate_working_hours(
			logs, self.determine_check_in_and_check_out, self.working_hours_calculation_based_on
		)
		if (
			cint(self.enable_entry_grace_period)
			and in_time
			and in_time > logs[0].shift_start + timedelta(minutes=cint(self.late_entry_grace_period))
		):
			late_entry = True

		if (
			cint(self.enable_exit_grace_period)
			and out_time
			and out_time < logs[0].shift_end - timedelta(minutes=cint(self.early_exit_grace_period))
		):
			early_exit = True

		if (
			self.working_hours_threshold_for_half_day
			and total_working_hours < self.working_hours_threshold_for_half_day
		):
			return "Half Day", total_working_hours, late_entry, early_exit, in_time, out_time
		if (
			self.working_hours_threshold_for_absent
			and total_working_hours < self.working_hours_threshold_for_absent
		):
			return "Absent", total_working_hours, late_entry, early_exit, in_time, out_time
		return "Present", total_working_hours, late_entry, early_exit, in_time, out_time

	def mark_absent_for_dates_with_no_attendance(self, employee):
		"""Marks Absents for the given employee on working days in this shift which have no attendance marked.
		The Absent is marked starting from 'process_attendance_after' or employee creation date.
		"""
		start_date, end_date = self.get_start_and_end_dates(employee)

		# no shift assignment found, no need to process absent attendance records
		if start_date is None:
			return

		holiday_list_name = self.holiday_list
		if not holiday_list_name:
			holiday_list_name = get_holiday_list_for_employee(employee, False)

		start_time = get_time(self.start_time)

		for date in daterange(getdate(start_date), getdate(end_date)):
			if is_holiday(holiday_list_name, date):
				# skip marking absent on a holiday
				continue

			timestamp = datetime.combine(date, start_time)
			shift_details = get_employee_shift(employee, timestamp, True)

			if shift_details and shift_details.shift_type.name == self.name:
				mark_attendance(employee, date, "Absent", self.name)

	def get_start_and_end_dates(self, employee):
		"""Returns start and end dates for checking attendance and marking absent
		return: start date = max of `process_attendance_after` and DOJ
		return: end date = min of shift before `last_sync_of_checkin` and Relieving Date
		"""
		date_of_joining, relieving_date, employee_creation = frappe.db.get_value(
			"Employee", employee, ["date_of_joining", "relieving_date", "creation"]
		)

		if not date_of_joining:
			date_of_joining = employee_creation.date()

		start_date = max(getdate(self.process_attendance_after), date_of_joining)
		end_date = None

		shift_details = get_shift_details(self.name, get_datetime(self.last_sync_of_checkin))
		last_shift_time = (
			shift_details.actual_start if shift_details else get_datetime(self.last_sync_of_checkin)
		)

		# check if shift is found for 1 day before the last sync of checkin
		# absentees are auto-marked 1 day after the shift to wait for any manual attendance records
		prev_shift = get_employee_shift(employee, last_shift_time - timedelta(days=1), True, "reverse")
		if prev_shift:
			end_date = (
				min(prev_shift.start_datetime.date(), relieving_date)
				if relieving_date
				else prev_shift.start_datetime.date()
			)
		else:
			# no shift found
			return None, None
		return start_date, end_date

	def get_assigned_employee(self, from_date=None, consider_default_shift=False):
		filters = {"shift_type": self.name, "docstatus": "1"}
		if from_date:
			filters["start_date"] = (">", from_date)

		assigned_employees = frappe.get_all("Shift Assignment", filters=filters, pluck="employee")

		if consider_default_shift:
			filters = {"default_shift": self.name, "status": ["!=", "Inactive"]}
			default_shift_employees = frappe.get_all("Employee", filters=filters, pluck="name")

			return list(set(assigned_employees + default_shift_employees))
		return assigned_employees


def process_auto_attendance_for_all_shifts():
	shift_list = frappe.get_all("Shift Type", "name", {"enable_auto_attendance": "1"}, as_list=True)
	for shift in shift_list:
		doc = frappe.get_doc("Shift Type", shift[0])
		doc.process_auto_attendance()
