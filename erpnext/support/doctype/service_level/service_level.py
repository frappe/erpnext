# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from datetime import datetime
from frappe.utils import get_weekdays

class ServiceLevel(Document):

	def validate(self):
		week = get_weekdays()
		indexes = []

		self.check_response_and_resolution_time()

		for support_and_resolution in self.support_and_resolution:
			indexes.append(week.index(support_and_resolution.workday))
			support_and_resolution.idx = week.index(support_and_resolution.workday) + 1
			start_time, end_time = (datetime.strptime(support_and_resolution.start_time, '%H:%M:%S').time(),
				datetime.strptime(support_and_resolution.end_time, '%H:%M:%S').time())
			if start_time > end_time:
				frappe.throw(_("Start Time can't be greater than End Time for {0}.".format(support_and_resolution.workday)))
		if not len(set(indexes)) == len(indexes):
			frappe.throw(_("Workday has been repeated twice"))

	def check_response_and_resolution_time(self):
		if self.response_time_period == "Hour":
			response = self.response_time * 0.0416667
		elif self.response_time_period == "Day":
			response = self.response_time
		elif self.response_time_period == "Week":
			response = self.response_time * 7

		if self.resolution_time_period == "Hour":
			resolution = self.resolution_time * 0.0416667
		elif self.resolution_time_period == "Day":
			resolution = self.resolution_time
		elif self.resolution_time_period == "Week":
			resolution = self.resolution_time * 7

		if response > resolution:
			frappe.throw(_("Response Time can't be greater than Resolution Time"))