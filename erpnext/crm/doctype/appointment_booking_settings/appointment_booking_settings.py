# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import datetime
from frappe.model.document import Document

class AppointmentBookingSettings(Document):
	def validate(self):
		# Day of week should not be repeated
		list_of_days = []
		date = '01/01/1970 '
		format_string = "%d/%m/%Y %H:%M:%S"
		for record in self.availability_of_slots:
			list_of_days.append(record.day_of_week)
			# Difference between from_time and to_time is multiple of appointment_duration
			from_time = datetime.datetime.strptime(date+record.from_time,format_string)
			to_time = datetime.datetime.strptime(date+record.to_time,format_string)
			timedelta = to_time-from_time
			if(from_time>to_time):
				frappe.throw('From Time cannot be later than To Time for '+record.day_of_week)
			if timedelta.total_seconds() % (self.appointment_duration*60):
				frappe.throw('The difference between from time and To Time must be a multiple of Appointment ')
		set_of_days = set(list_of_days)
		if len(list_of_days) > len(set_of_days):
			frappe.throw(_('Days of week must be unique'))
	
