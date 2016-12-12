# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class StudentAttendance(Document):
	def validate(self):
		self.validate_date()
		self.validate_mandatory()
		self.validate_duplication()
		
	def validate_date(self):
		if self.course_schedule:
			self.date = frappe.db.get_value("Course Schedule", self.course_schedule, "schedule_date")
	
	def validate_mandatory(self):
		if not (self.student_batch or self.course_schedule):
			frappe.throw(_("""Student Batch or Course Schedule is mandatory"""))
	
	def validate_duplication(self):
		"""Check if the Attendance Record is Unique"""
		
		attendance_records=None
		if self.course_schedule:
			attendance_records= frappe.db.sql("""select name from `tabStudent Attendance` where \
				student= %s and course_schedule= %s and name != %s and docstatus=1""",
				(self.student, self.course_schedule, self.name))
		else:
			attendance_records= frappe.db.sql("""select name from `tabStudent Attendance` where \
				student= %s and student_batch= %s and date= %s and name != %s and docstatus=1 and \
				(course_schedule is Null or course_schedule='')""",
				(self.student, self.student_batch, self.date, self.name))
			
		if attendance_records:
			frappe.throw(_("Attendance Record {0} exists against Student {1}")
				.format(attendance_records[0][0], self.student))
