# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _, msgprint
from frappe.desk.reportview import get_match_cond
from frappe.model.document import Document
from frappe.utils import comma_and, get_link_to_form, getdate


class ProgramEnrollment(Document):
	def validate(self):
		self.validate_duplication()
		self.validate_academic_year()
		if self.academic_term:
			self.validate_academic_term()
		if not self.student_name:
			self.student_name = frappe.db.get_value("Student", self.student, "title")
		if not self.courses:
			self.extend("courses", self.get_courses())

	def on_submit(self):
		self.update_student_joining_date()
		self.make_fee_records()
		self.create_course_enrollments()

	def validate_academic_year(self):
		start_date, end_date = frappe.db.get_value("Academic Year", self.academic_year, ["year_start_date", "year_end_date"])
		if self.enrollment_date:
			if start_date and getdate(self.enrollment_date) < getdate(start_date):
				frappe.throw(_("Enrollment Date cannot be before the Start Date of the Academic Year {0}").format(
					get_link_to_form("Academic Year", self.academic_year)))

			if end_date and getdate(self.enrollment_date) > getdate(end_date):
				frappe.throw(_("Enrollment Date cannot be after the End Date of the Academic Term {0}").format(
					get_link_to_form("Academic Year", self.academic_year)))

	def validate_academic_term(self):
		start_date, end_date = frappe.db.get_value("Academic Term", self.academic_term, ["term_start_date", "term_end_date"])
		if self.enrollment_date:
			if start_date and getdate(self.enrollment_date) < getdate(start_date):
				frappe.throw(_("Enrollment Date cannot be before the Start Date of the Academic Term {0}").format(
					get_link_to_form("Academic Term", self.academic_term)))

			if end_date and getdate(self.enrollment_date) > getdate(end_date):
				frappe.throw(_("Enrollment Date cannot be after the End Date of the Academic Term {0}").format(
					get_link_to_form("Academic Term", self.academic_term)))

	def validate_duplication(self):
		enrollment = frappe.get_all("Program Enrollment", filters={
			"student": self.student,
			"program": self.program,
			"academic_year": self.academic_year,
			"academic_term": self.academic_term,
			"docstatus": ("<", 2),
			"name": ("!=", self.name)
		})
		if enrollment:
			frappe.throw(_("Student is already enrolled."))

	def update_student_joining_date(self):
		date = frappe.db.sql("select min(enrollment_date) from `tabProgram Enrollment` where student= %s", self.student)
		frappe.db.set_value("Student", self.student, "joining_date", date)

	def make_fee_records(self):
		from erpnext.education.api import get_fee_components
		fee_list = []
		for d in self.fees:
			fee_components = get_fee_components(d.fee_structure)
			if fee_components:
				fees = frappe.new_doc("Fees")
				fees.update({
					"student": self.student,
					"academic_year": self.academic_year,
					"academic_term": d.academic_term,
					"fee_structure": d.fee_structure,
					"program": self.program,
					"due_date": d.due_date,
					"student_name": self.student_name,
					"program_enrollment": self.name,
					"components": fee_components
				})

				fees.save()
				fees.submit()
				fee_list.append(fees.name)
		if fee_list:
			fee_list = ["""<a href="/app/Form/Fees/%s" target="_blank">%s</a>""" % \
				(fee, fee) for fee in fee_list]
			msgprint(_("Fee Records Created - {0}").format(comma_and(fee_list)))


	@frappe.whitelist()
	def get_courses(self):
		return frappe.db.sql('''select course from `tabProgram Course` where parent = %s and required = 1''', (self.program), as_dict=1)

	def create_course_enrollments(self):
		student = frappe.get_doc("Student", self.student)
		course_list = [course.course for course in self.courses]
		for course_name in course_list:
			student.enroll_in_course(course_name=course_name, program_enrollment=self.name, enrollment_date=self.enrollment_date)

	def get_all_course_enrollments(self):
		course_enrollment_names = frappe.get_list("Course Enrollment", filters={'program_enrollment': self.name})
		return [frappe.get_doc('Course Enrollment', course_enrollment.name) for course_enrollment in course_enrollment_names]

	def get_quiz_progress(self):
		student = frappe.get_doc("Student", self.student)
		quiz_progress = frappe._dict()
		progress_list = []
		for course_enrollment in self.get_all_course_enrollments():
			course_progress = course_enrollment.get_progress(student)
			for progress_item in course_progress:
				if progress_item['content_type'] == "Quiz":
					progress_item['course'] = course_enrollment.course
					progress_list.append(progress_item)
		if not progress_list:
			return None
		quiz_progress.quiz_attempt = progress_list
		quiz_progress.name = self.program
		quiz_progress.program = self.program
		return quiz_progress

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_program_courses(doctype, txt, searchfield, start, page_len, filters):
	if not filters.get('program'):
		frappe.msgprint(_("Please select a Program first."))
		return []

	return frappe.db.sql("""select course, course_name from `tabProgram Course`
		where  parent = %(program)s and course like %(txt)s {match_cond}
		order by
			if(locate(%(_txt)s, course), locate(%(_txt)s, course), 99999),
			idx desc,
			`tabProgram Course`.course asc
		limit {start}, {page_len}""".format(
			match_cond=get_match_cond(doctype),
			start=start,
			page_len=page_len), {
				"txt": "%{0}%".format(txt),
				"_txt": txt.replace('%', ''),
				"program": filters['program']
			})

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_students(doctype, txt, searchfield, start, page_len, filters):
	if not filters.get("academic_term"):
		filters["academic_term"] = frappe.defaults.get_defaults().academic_term

	if not filters.get("academic_year"):
		filters["academic_year"] = frappe.defaults.get_defaults().academic_year

	enrolled_students = frappe.get_list("Program Enrollment", filters={
		"academic_term": filters.get('academic_term'),
		"academic_year": filters.get('academic_year')
	}, fields=["student"])

	students = [d.student for d in enrolled_students] if enrolled_students else [""]

	return frappe.db.sql("""select
			name, title from tabStudent
		where
			name not in (%s)
		and
			`%s` LIKE %s
		order by
			idx desc, name
		limit %s, %s"""%(
			", ".join(['%s']*len(students)), searchfield, "%s", "%s", "%s"),
			tuple(students + ["%%%s%%" % txt, start, page_len]
		)
	)
