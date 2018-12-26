# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from datetime import datetime

class ServiceLevel(Document):

	def validate(self):
		week = ["Monday",  "Tuesday",  "Wednesday",  "Thursday", "Friday", "Saturday", "Sunday"]
		indexes = []
		
		for support_and_resolution in self.support_and_resolution:
			indexes.append(week.index(support_and_resolution.workday))
			support_and_resolution.idx = week.index(support_and_resolution.workday) + 1
			start_time, end_time = datetime.strptime(support_and_resolution.start_time, '%H:%M:%S').time(), datetime.strptime(support_and_resolution.end_time, '%H:%M:%S').time()
			if start_time > end_time:
				frappe.throw(_("Start Time can't be greater than End Time for "+ support_and_resolution.workday +"."))

		if not len(set(indexes)) == len(indexes):
			frappe.throw(_("Workday has been repeated twice"))