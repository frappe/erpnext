# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.desk.form.linked_with import get_linked_doctypes

class Student(Document):
	def validate(self):
		self.title = " ".join(filter(None, [self.first_name, self.middle_name, self.last_name]))

		if self.student_applicant:
			self.check_unique()
			self.update_applicant_status()

		if frappe.get_value("Student", self.name, "title") != self.title:
			self.update_student_name_in_linked_doctype()

	def update_student_name_in_linked_doctype(self):
		linked_doctypes = get_linked_doctypes("Student")
		for d in linked_doctypes:
			meta = frappe.get_meta(d)
			if not meta.issingle:
				if "student_name" in [f.fieldname for f in meta.fields]:
					frappe.db.sql("""UPDATE `tab{0}` set student_name = %s where {1} = %s"""
						.format(d, linked_doctypes[d]["fieldname"][0]),(self.title, self.name))

				if "child_doctype" in linked_doctypes[d].keys() and "student_name" in \
					[f.fieldname for f in frappe.get_meta(linked_doctypes[d]["child_doctype"]).fields]:
					frappe.db.sql("""UPDATE `tab{0}` set student_name = %s where {1} = %s"""
						.format(linked_doctypes[d]["child_doctype"], linked_doctypes[d]["fieldname"][0]),(self.title, self.name))

	def check_unique(self):
		"""Validates if the Student Applicant is Unique"""
		student = frappe.db.sql("select name from `tabStudent` where student_applicant=%s and name!=%s", (self.student_applicant, self.name))
		if student:
			frappe.throw(_("Student {0} exist against student applicant {1}").format(student[0][0], self.student_applicant))

	def update_applicant_status(self):
		"""Updates Student Applicant status to Admitted"""
		if self.student_applicant:
			frappe.db.set_value("Student Applicant", self.student_applicant, "application_status", "Admitted")

	def get_course_enrollments(self):
		"""Returns a list of course enrollments linked with the current student"""
		course_enrollments = frappe.get_list("Course Enrollment", filters={"student": self.name}, fields=['name'])
		if not course_enrollments:
			return None
		else:
			enrollments = [item['name'] for item in course_enrollments]
			return enrollments

	def get_program_enrollments(self):
		"""Returns a list of course enrollments linked with the current student"""
		program_enrollments = frappe.get_list("Program Enrollment", filters={"student": self.name}, fields=['program'])
		if not program_enrollments:
			return None
		else:
			enrollments = [item['program'] for item in program_enrollments]
			return enrollments

	def get_completed_courses(self):
		"""Returns a list of course enrollments linked with the current student"""
		completed_courses = frappe.get_list("Course Enrollment", filters={"student": self.name, "completed":1}, fields=['course'])
		if not completed_courses:
			return None
		else:
			courses = [item['course'] for item in completed_courses]
			return courses

	def enroll_in_program(self, program_name):
		enrollment = frappe.get_doc({
				"doctype": "Program Enrollment",
				"student": self.name,
				"academic_year": frappe.get_last_doc("Academic Year").name,
				"program": program_name,
				"enrollment_date": frappe.utils.datetime.datetime.now()
			})
		enrollment.save()
		enrollment.submit()
		frappe.db.commit()
		return enrollment

	def enroll_in_course(self, course_name, program_enrollment, enrollment_date=frappe.utils.datetime.datetime.now()):
		enrollment = frappe.get_doc({
				"doctype": "Course Enrollment",
				"student": self.name,
				"course": course_name,
				"program_enrollment": program_enrollment,
				"enrollment_date": enrollment_date
			})
		enrollment.save()
		frappe.db.commit()

def get_timeline_data(doctype, name):
	'''Return timeline for attendance'''
	return dict(frappe.db.sql('''select unix_timestamp(`date`), count(*)
		from `tabStudent Attendance` where
			student=%s
			and `date` > date_sub(curdate(), interval 1 year)
			and status = 'Present'
			group by date''', name))
