# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate,today
from frappe import _
from frappe.desk.form.linked_with import get_linked_doctypes
from erpnext.education.utils import check_content_completion, check_quiz_completion
class Student(Document):
	def validate(self):
		self.title = " ".join(filter(None, [self.first_name, self.middle_name, self.last_name]))
		self.validate_dates()

		if self.student_applicant:
			self.check_unique()
			self.update_applicant_status()

		if frappe.get_value("Student", self.name, "title") != self.title:
			self.update_student_name_in_linked_doctype()

	def validate_dates(self):
		for sibling in self.siblings:
			if sibling.date_of_birth and getdate(sibling.date_of_birth) > getdate():
				frappe.throw(_("Row {0}:Sibling Date of Birth cannot be greater than today.").format(sibling.idx))

		if self.date_of_birth and getdate(self.date_of_birth) >= getdate(today()):
			frappe.throw(_("Date of Birth cannot be greater than today."))

		if self.date_of_birth and getdate(self.date_of_birth) >= getdate(self.joining_date):
			frappe.throw(_("Date of Birth cannot be greater than Joining Date."))

		if self.joining_date and self.date_of_leaving and getdate(self.joining_date) > getdate(self.date_of_leaving):
			frappe.throw(_("Joining Date can not be greater than Leaving Date"))

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

	def after_insert(self):
		if not frappe.get_single('Education Settings').get('user_creation_skip'):
			self.create_student_user()

	def create_student_user(self):
		"""Create a website user for student creation if not already exists"""
		if not frappe.db.exists("User", self.student_email_id):
			student_user = frappe.get_doc({
				'doctype':'User',
				'first_name': self.first_name,
				'last_name': self.last_name,
				'email': self.student_email_id,
				'gender': self.gender,
				'send_welcome_email': 1,
				'user_type': 'Website User'
				})
			student_user.flags.ignore_permissions = True
			student_user.add_roles("Student")
			student_user.save()
			update_password_link = student_user.reset_password()

	def update_applicant_status(self):
		"""Updates Student Applicant status to Admitted"""
		if self.student_applicant:
			frappe.db.set_value("Student Applicant", self.student_applicant, "application_status", "Admitted")

	def get_all_course_enrollments(self):
		"""Returns a list of course enrollments linked with the current student"""
		course_enrollments = frappe.get_all("Course Enrollment", filters={"student": self.name}, fields=['course', 'name'])
		if not course_enrollments:
			return None
		else:
			enrollments = {item['course']:item['name'] for item in course_enrollments}
			return enrollments

	def get_program_enrollments(self):
		"""Returns a list of course enrollments linked with the current student"""
		program_enrollments = frappe.get_all("Program Enrollment", filters={"student": self.name}, fields=['program'])
		if not program_enrollments:
			return None
		else:
			enrollments = [item['program'] for item in program_enrollments]
			return enrollments

	def get_topic_progress(self, course_enrollment_name, topic):
		"""
		Get Progress Dictionary of a student for a particular topic
			:param self: Student Object
			:param course_enrollment_name: Name of the Course Enrollment
			:param topic: Topic DocType Object
		"""
		contents = topic.get_contents()
		progress = []
		if contents:
			for content in contents:
				if content.doctype in ('Article', 'Video'):
					status = check_content_completion(content.name, content.doctype, course_enrollment_name)
					progress.append({'content': content.name, 'content_type': content.doctype, 'is_complete': status})
				elif content.doctype == 'Quiz':
					status, score, result = check_quiz_completion(content, course_enrollment_name)
					progress.append({'content': content.name, 'content_type': content.doctype, 'is_complete': status, 'score': score, 'result': result})
		return progress

	def enroll_in_program(self, program_name):
		try:
			enrollment = frappe.get_doc({
					"doctype": "Program Enrollment",
					"student": self.name,
					"academic_year": frappe.get_last_doc("Academic Year").name,
					"program": program_name,
					"enrollment_date": frappe.utils.datetime.datetime.now()
				})
			enrollment.save(ignore_permissions=True)
		except frappe.exceptions.ValidationError:
			enrollment_name = frappe.get_list("Program Enrollment", filters={"student": self.name, "Program": program_name})[0].name
			return frappe.get_doc("Program Enrollment", enrollment_name)
		else:
			enrollment.submit()
			return enrollment

	def enroll_in_course(self, course_name, program_enrollment, enrollment_date=frappe.utils.datetime.datetime.now()):
		try:
			enrollment = frappe.get_doc({
					"doctype": "Course Enrollment",
					"student": self.name,
					"course": course_name,
					"program_enrollment": program_enrollment,
					"enrollment_date": enrollment_date
				})
			enrollment.save(ignore_permissions=True)
		except frappe.exceptions.ValidationError:
			enrollment_name = frappe.get_list("Course Enrollment", filters={"student": self.name, "course": course_name, "program_enrollment": program_enrollment})[0].name
			return frappe.get_doc("Course Enrollment", enrollment_name)
		else:
			return enrollment

def get_timeline_data(doctype, name):
	'''Return timeline for attendance'''
	return dict(frappe.db.sql('''select unix_timestamp(`date`), count(*)
		from `tabStudent Attendance` where
			student=%s
			and `date` > date_sub(curdate(), interval 1 year)
			and docstatus = 1 and status = 'Present'
			group by date''', name))
