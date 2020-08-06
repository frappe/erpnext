# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import get_link_to_form
from erpnext.education.api import get_student_group_students


class StudentAttendance(Document):
	def validate(self):
		self.validate_mandatory()
		self.set_date()
		self.set_student_group()
		self.validate_student()
		self.validate_duplication()

	def set_date(self):
		if self.course_schedule:
			self.date = frappe.db.get_value('Course Schedule', self.course_schedule, 'schedule_date')

	def validate_mandatory(self):
		if not (self.student_group or self.course_schedule):
			frappe.throw(_('{0} or {1} is mandatory').format(frappe.bold('Student Group'),
				frappe.bold('Course Schedule')), title=_('Mandatory Fields'))

	def set_student_group(self):
		if self.course_schedule:
			self.student_group = frappe.db.get_value('Course Schedule', self.course_schedule, 'student_group')

	def validate_student(self):
		if self.course_schedule:
			student_group = frappe.db.get_value('Course Schedule', self.course_schedule, 'student_group')
		else:
			student_group = self.student_group
		student_group_students = [d.student for d in get_student_group_students(student_group)]
		if student_group and self.student not in student_group_students:
			student_group_doc = get_link_to_form('Student Group', student_group)
			frappe.throw(_('Student {0}: {1} does not belong to Student Group {2}').format(
				frappe.bold(self.student), self.student_name, frappe.bold(student_group_doc)))

	def validate_duplication(self):
		"""Check if the Attendance Record is Unique"""
		attendance_record = None
		if self.course_schedule:
			attendance_record = frappe.db.exists('Student Attendance', {
				'student': self.student,
				'course_schedule': self.course_schedule,
				'docstatus': ('!=', 2),
				'name': ('!=', self.name)
			})
		else:
			attendance_record = frappe.db.exists('Student Attendance', {
				'student': self.student,
				'student_group': self.student_group,
				'date': self.date,
				'docstatus': ('!=', 2),
				'name': ('!=', self.name),
				'course_schedule': ''
			})

		if attendance_record:
			record = get_link_to_form('Attendance Record', attendance_record)
			frappe.throw(_('Student Attendance record {0} already exists against the Student {1}')
				.format(record, frappe.bold(self.student)), title=_('Duplicate Entry'))
