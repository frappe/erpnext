# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
from frappe.utils import cstr

class PrescriptionDuration(Document):
	def autoname(self):
		self.name = " ".join(filter(None,
			[cstr(self.get(f)).strip() for f in ["number", "period"]]))
	def get_days(self):
		days = 0
		duration = self
		if(duration.period == 'Day'):
			days = duration.number
		if(duration.period == 'Hour'):
			days = (duration.number)/24
		if(duration.period == 'Week'):
			days = (duration.number*7)
		if(duration.period == 'Month'):
			days = (duration.number*30)
		return days
	def get_weeks(self):
		weeks = 0
		duration = self
		if(duration.period == 'Day'):
			weeks = (duration.number)/7
		#if(duration.period == 'Hour'):
		#	weeks = (duration.number)/x
		if(duration.period == 'Week'):
			weeks = duration.number
		if(duration.period == 'Month'):
			weeks = duration.number*4
		return weeks
	def get_months(self):
		months = 0
		duration = self
		if(duration.period == 'Day'):
			months = (duration.number)/30
		#if(duration.period == 'Hour'):
		#	months = (duration.number)/x
		if(duration.period == 'Week'):
			months = (duration.number)/4
		if(duration.period == 'Month'):
			months = duration.number
		return months
	def get_hours(self):
		hours = 0
		duration = self
		if(duration.period == 'Day'):
			hours = (duration.number*24)
		if(duration.period == 'Hour'):
			hours = duration.number
		if(duration.period == 'Week'):
			hours = (duration.number*24)*7
		if(duration.period == 'Month'):
			hours = (duration.number*24)*30
		return hours
	def get_minutes(self):
		minutes = 0
		duration = self
		if(duration.period == 'Day'):
			minutes = (duration.number*1440)
		if(duration.period == 'Hour'):
			minutes = (duration.number*60)
		if(duration.period == 'Week'):
			minutes = (duration.number*10080)
		if(duration.period == 'Month'):
			minutes = (duration.number*43800)
		return minutes
