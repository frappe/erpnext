# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class StudentCourseActivity(Document):
	def validate(self):
		self.check_if_enrolled()
		# self.check_if_course_present()

	def check_if_enrolled(self):
		programs_list = frappe.get_list("Program Enrollment", filters={'student': self.student_name}, fields=['program'])
		programs_enrolled_by_student = [item.program for item in programs_list]
		if self.program_name not in programs_enrolled_by_student:
			frappe.throw("Student <b>{0}</b> is not enrolled in <b>program {1}</b> ".format(self.student_name, self.program_name))

	# def check_if_course_present(self):
	# 	""" Get set of unique courses from lms_activity child table and make a list of it as assign it to course_list"""
	# 	course_list = list(set([activity.course_name for activity in self.lms_activity]))
	# 	current_program = frappe.get_doc('Program', self.program_name)
	# 	courses_in_current_program = [course.course_name for course in current_program.courses]
	# 	if len(set(courses_in_current_program) - set(course_list)) == 0: