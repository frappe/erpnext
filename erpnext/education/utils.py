# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For lice

from __future__ import unicode_literals, division
import frappe
from frappe import _

class OverlapError(frappe.ValidationError): pass

def validate_overlap_for(doc, doctype, fieldname, value=None):
	"""Checks overlap for specified field.

	:param fieldname: Checks Overlap for this field
	"""

	existing = get_overlap_for(doc, doctype, fieldname, value)
	if existing:
		frappe.throw(_("This {0} conflicts with {1} for {2} {3}").format(doc.doctype, existing.name,
			doc.meta.get_label(fieldname) if not value else fieldname , value or doc.get(fieldname)), OverlapError)

def get_overlap_for(doc, doctype, fieldname, value=None):
	"""Returns overlaping document for specified field.

	:param fieldname: Checks Overlap for this field
	"""

	existing = frappe.db.sql("""select name, from_time, to_time from `tab{0}`
		where `{1}`=%(val)s and schedule_date = %(schedule_date)s and
		(
			(from_time > %(from_time)s and from_time < %(to_time)s) or
			(to_time > %(from_time)s and to_time < %(to_time)s) or
			(%(from_time)s > from_time and %(from_time)s < to_time) or
			(%(from_time)s = from_time and %(to_time)s = to_time))
		and name!=%(name)s and docstatus!=2""".format(doctype, fieldname),
		{
			"schedule_date": doc.schedule_date,
			"val": value or doc.get(fieldname),
			"from_time": doc.from_time,
			"to_time": doc.to_time,
			"name": doc.name or "No Name"
		}, as_dict=True)

	return existing[0] if existing else None


def validate_duplicate_student(students):
	unique_students= []
	for stud in students:
		if stud.student in unique_students:
			frappe.throw(_("Student {0} - {1} appears Multiple times in row {2} & {3}")
				.format(stud.student, stud.student_name, unique_students.index(stud.student)+1, stud.idx))
		else:
			unique_students.append(stud.student)

		return None

# LMS Utils
def get_current_student():
	"""
	Returns student user name, example EDU-STU-2018-00001 (Based on the naming series).
	Takes email from from frappe.session.user
	"""
	email = frappe.session.user
	if email in ('Administrator', 'Guest'):
		return None
	try:
		student_id = frappe.db.get_all("Student", {"student_email_id": email}, ["name"])[0].name
		return student_id
	except IndexError:
		return None

def get_program_enrollment(program_name):
	"""
	Function to get program enrollments for a particular student for a program
	"""
	student = get_current_student()
	if not student:
		return None
	else:
		enrollment = frappe.get_list("Program Enrollment", filters={'student':student, 'program': program_name})
		if enrollment:
			return enrollment[0].name
		else:
			return None

def get_program(program_name):
	program = frappe.get_doc('Program', program_name)
	is_enrolled = bool(get_program_enrollment(program_name))
	return {'program': program, 'is_enrolled': is_enrolled}

def get_course_enrollment(course_name):
	student = get_current_student()
	enrollment_name = frappe.get_all("Course Enrollment", filters={'student': student, 'course':course_name})
	try:
		name = enrollment_name[0].name
		enrollment = frappe.get_doc("Course Enrollment", name)
		return enrollment
	except:
		return None

def create_student():
	user = frappe.get_doc("User", frappe.session.user)
	student = frappe.get_doc({
		"doctype": "Student",
		"first_name": user.first_name,
		"last_name": user.last_name,
		"student_email_id": user.email,
		"user": frappe.session.user
		})
	student.save(ignore_permissions=True)
	frappe.db.commit()
	return student

def enroll_in_course(course_name, program_name):
	student_id = get_current_student()
	student = frappe.get_doc("Student", student_id)
	student.enroll_in_course(course_name=course_name, program_enrollment=get_program_enrollment(program_name))

def enroll_all_courses_in_program(program_enrollment, student):
	program = frappe.get_doc("Program", program_enrollment.program)
	course_list = [course.course for course in program.get_all_children()]
	for course_name in course_list:
		student.enroll_in_course(course_name=course_name, program_enrollment=program_enrollment.name)

def check_activity_exists(enrollment, content_type, content):
	activity = frappe.get_all("Course Activity", filters={'enrollment': enrollment, 'content_type': content_type, 'content': content})
	return bool(activity)

# def get_home_page(user):
# 	print("----------------------------------------------------------------------")
# 	print("Let's do a lot of magic")
# 	if get_current_student():
# 		return 'lms#/Profile'
# 	else:
# 		return None