# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, bold
from frappe.utils import get_link_to_form
from frappe.model.document import Document

class AttendanceStatus(Document):
	def validate(self):
		if self.is_present and self.is_leave and self.is_half_day:
			frappe.throw(_("Attendance status can either be Present, Leave or Half day."))

		self.validate_multiple_defaults()


	def validate_multiple_defaults(self):
		documents = []
		references = []
		if not self.is_leave and self.applicable_for_employee_checkins:
			att_status = self.get_duplicate(["is_present", "is_half_day", "is_leave"], "applicable_for_employee_checkins")
			if att_status:
				documents.append(att_status)
				references.append("Employee Checkin")

		if (self.is_half_day or self.is_leave) and self.applicable_for_leave_application:
			att_status = self.get_duplicate(["is_leave", "is_half_day"], "applicable_for_leave_application")
			if att_status:
				documents.append(att_status)
				references.append("Leave application")

		if self.is_half_day and self.applicable_for_attendance_request:
			att_status = self.get_duplicate(["is_half_day"], "applicable_for_attendance_request")
			if att_status:
				documents.append(att_status)
				references.append("Attendance Request")

		if len(documents) and len(references):
			self.throw_validation(references, documents)

	def get_duplicate(self, fields, status_property):
		filters= {}
		for field in fields:
			filters[field] = self.get(field)

		filters[status_property] = self.get(status_property)
		filters["name"]= ("!=", self.name)

		return frappe.db.exists("Attendance Status", filters)

	def throw_validation(self, references, documents):
		msg = ''
		for i in range(len(documents)):
			link = get_link_to_form(references[i], documents[i])
			msg += _("A Default Status for {0} already exists. {1} Reference : {2}").format(references[i], "<br>", bold(link)) + "<hr>"
		frappe.throw(msg)
