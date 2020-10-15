# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class AttendanceStatus(Document):
	def validate(self):
		if self.is_present and self.is_leave and self.is_half_day:
			frappe.throw(_("Attendance status can be either Present, leave or Half day"))
