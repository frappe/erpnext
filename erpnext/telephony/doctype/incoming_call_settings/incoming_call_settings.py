# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from datetime import datetime
from typing import Tuple

import frappe
from frappe import _
from frappe.model.document import Document


class IncomingCallSettings(Document):
	def validate(self):
		"""List of validations
		* Make sure that to time slot is ahead of from time slot in call schedule
		* Make sure that no overlapping timeslots for a given day
		"""
		self.validate_call_schedule_timeslot(self.call_handling_schedule)
		self.validate_call_schedule_overlaps(self.call_handling_schedule)

	def validate_call_schedule_timeslot(self, schedule: list):
		"""	Make sure that to time slot is ahead of from time slot.
		"""
		errors = []
		for record in schedule:
			from_time = self.time_to_seconds(record.from_time)
			to_time = self.time_to_seconds(record.to_time)
			if from_time >= to_time:
				errors.append(
					_('Call Schedule Row {0}: To time slot should always be ahead of From time slot.').format(record.idx)
				)

		if errors:
			frappe.throw('<br/>'.join(errors))

	def validate_call_schedule_overlaps(self, schedule: list):
		"""Check if any time slots are overlapped in a day schedule.
		"""
		week_days = set([each.day_of_week for each in schedule])

		for day in week_days:
			timeslots = [(record.from_time, record.to_time) for record in schedule if record.day_of_week==day]

			# convert time in timeslot into an integer represents number of seconds
			timeslots = sorted(map(lambda seq: tuple(map(self.time_to_seconds, seq)), timeslots))
			if len(timeslots) < 2: continue

			for i in range(1, len(timeslots)):
				if self.check_timeslots_overlap(timeslots[i-1], timeslots[i]):
					frappe.throw(_('Please fix overlapping time slots for {0}.').format(day))

	@staticmethod
	def check_timeslots_overlap(ts1: Tuple[int, int], ts2: Tuple[int, int]) -> bool:
		if (ts1[0] < ts2[0] and ts1[1] <= ts2[0]) or (ts1[0] >= ts2[1] and ts1[1] > ts2[1]):
			return False
		return True

	@staticmethod
	def time_to_seconds(time: str) -> int:
		"""Convert time string of format HH:MM:SS into seconds
		"""
		date_time = datetime.strptime(time, "%H:%M:%S")
		return date_time - datetime(1900, 1, 1)
