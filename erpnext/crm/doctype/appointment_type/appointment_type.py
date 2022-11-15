# -*- coding: utf-8 -*-
# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import datetime
from frappe import _
from frappe.utils import getdate, combine_datetime, cint, get_datetime
from frappe.model.document import Document
from erpnext.hr.doctype.holiday_list.holiday_list import get_default_holiday_list


class AppointmentType(Document):
	min_date = '01/01/1970 '
	format_string = "%d/%m/%Y %H:%M:%S"

	def validate(self):
		self.validate_appointment_duration()
		self.validate_number_of_agents()
		self.validate_availability_of_slots()

	def validate_appointment_duration(self):
		self.appointment_duration = cint(self.appointment_duration)
		if cint(self.appointment_duration) < 0:
			frappe.throw(_("Appointment Duration cannot be negative"))

	def validate_number_of_agents(self):
		if self.get('agent_list'):
			self.number_of_agents = len(self.agent_list)

		if cint(self.number_of_agents) <= 0:
			frappe.throw(_("Number of Available Agents must be a positive number"))

	def validate_availability_of_slots(self):
		for record in self.availability_of_slots:
			from_time = datetime.datetime.strptime(self.min_date + record.from_time, self.format_string)
			to_time = datetime.datetime.strptime(self.min_date + record.to_time, self.format_string)
			self.validate_from_and_to_time(record, from_time, to_time)
			self.duration_is_divisible(from_time, to_time)

	def validate_from_and_to_time(self, record, from_time, to_time):
		if from_time > to_time:
			frappe.throw(_('<b>From Time</b> cannot be later than <b>To Time</b> on {0}').format(record.day_of_week))

	def duration_is_divisible(self, from_time, to_time):
		timedelta = to_time - from_time
		if timedelta.total_seconds() % (self.appointment_duration * 60):
			frappe.throw(_('The difference between from time and To Time must be a multiple of Appointment Duration'))

	def is_in_timeslot(self, start_dt, end_dt=None, duration=None):
		start_dt = get_datetime(start_dt)

		timeslot_range = self.get_timeslot_range(start_dt)
		if timeslot_range is None:
			return True

		if end_dt:
			duration = end_dt - start_dt
		elif cint(duration) > 0:
			duration = datetime.timedelta(minutes=duration)
			end_dt = start_dt + duration

		# if no availability data then allow
		if timeslot_range is None:
			return True

		for range_start, range_end in timeslot_range:
			in_range = True
			if not time_in_range(range_start, range_end, start_dt):
				in_range = False

			if end_dt and not time_in_range(range_start, range_end, end_dt):
				in_range = False

			if in_range:
				return True

		return False

	def get_timeslots(self, date):
		timeslot_range = self.get_timeslot_range(date)
		if timeslot_range is None:
			return None

		if cint(self.appointment_duration) <= 0:
			return None

		appointment_duration = datetime.timedelta(minutes=cint(self.appointment_duration))

		timeslots = []
		for start_dt, end_dt in timeslot_range:
			timeslot_start = start_dt
			while timeslot_start + appointment_duration <= end_dt:
				timeslot_end = timeslot_start + appointment_duration
				timeslots.append((timeslot_start, timeslot_end))
				timeslot_start += appointment_duration

		timeslots = sorted(timeslots, key=lambda d: (d[0], d[1]))
		return timeslots

	def get_timeslot_range(self, date):
		if not self.get('availability_of_slots'):
			return None

		date = getdate(date)
		day_of_week = frappe.utils.formatdate(date, "EEEE")

		timeslot_rows = [d for d in self.availability_of_slots if d.day_of_week == day_of_week]
		timeslot_range = [(combine_datetime(date, d.from_time), combine_datetime(date, d.to_time)) for d in timeslot_rows]

		return timeslot_range

	def is_holiday(self, date, company):
		from erpnext.hr.doctype.holiday_list.holiday_list import is_holiday
		date = getdate(date)
		holiday_list = self.get_holiday_list(company)
		return is_holiday(holiday_list, date)

	def get_holiday_list(self, company):
		if self.get('holiday_list'):
			return self.holiday_list
		elif company:
			return get_default_holiday_list(company)
		else:
			return None

	def get_agents(self):
		return [agent.user for agent in self.agent_list]


def time_in_range(start, end, x):
	"""Return true if x is in the range [start, end]"""
	if start <= end:
		return start <= x <= end
	else:
		return start <= x or x <= end
