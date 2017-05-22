# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import throw, _
from frappe.model.document import Document
from frappe.utils.data import get_datetime, time_diff_in_hours, cint,flt

class AttendanceHours(Document):
	def validate(self):
		self.validate_hours()

	def validate_hours(self):
		if self.attendance_hours:
			if int(self.attendance_hours)<1 or int(self.attendance_hours)>24:
				frappe.throw(_("Bad Value set value between 1 and 24 hours<br> {0}").format(self.attendance_hours))

		#~ if get_datetime(self.start_time) > get_datetime(self.end_time):
			#~ frappe.throw(_("Start Time must be less than End Time"))

		if self.break_hours and time_diff_in_hours(get_datetime(self.end_time), get_datetime(self.start_time)) < cint(self.break_hours):
			frappe.throw(_("The period between Start Time and End Time must be greater than Break Hours"))


		#~ if flt(self.attendance_hours) != time_diff_in_hours(get_datetime(self.end_time), get_datetime(self.start_time)):
			#~ frappe.throw(_("The Attendance Hours must equal period between Start Time and End Time"))
