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

def get_student_name(email=None):
	"""Returns student user name, example EDU-STU-2018-00001 (Based on the naming series).
	
	:param user: a user email address
	"""
	try:
		return frappe.get_all('Student', filters={'student_email_id': email}, fields=['name'])[0].name
	except IndexError:
		return None

@frappe.whitelist()
def evaluate_quiz(quiz_response, **kwargs):
	"""LMS Function: Evaluates a simple multiple choice quiz.  It recieves arguments from `www/lms/course.js` as dictionary using FormData[1].
	

	:param quiz_response: contains user selected choices for a quiz in the form of a string formatted as a dictionary. The function uses `json.loads()` to convert it to a python dictionary.
	[1]: https://developer.mozilla.org/en-US/docs/Web/API/FormData
	"""
	import json
	quiz_response = json.loads(quiz_response)
	correct_answers = [frappe.get_value('Question', name, 'correct_options') for name in quiz_response.keys()]
	selected_options = quiz_response.values()
	result = [selected == correct for selected, correct in zip(selected_options, correct_answers)]
	try:
		score = int((result.count(True)/len(selected_options))*100)
	except ZeroDivisionError:
		score = 0

	kwargs['selected_options'] = selected_options
	kwargs['result'] = result
	kwargs['score'] = score
	add_activity('Quiz', **kwargs)
	return score

@frappe.whitelist()
def add_activity(content_type, **kwargs):
	activity_does_not_exists, activity = check_entry_exists(kwargs.get('program'))
	if activity_does_not_exists:
		current_activity = frappe.get_doc({
			"doctype": "Course Activity",
			"student_id": get_student_id(frappe.session.user),
			"program_name": kwargs.get('program'),
			"lms_activity": [{
				"course_name": kwargs.get('course'),
				"content_name": kwargs.get('content'),
				"status": "Completed"
				}]
			})
		if content_type == "Quiz":
			activity = current_activity.lms_activity[-1]
			activity.quiz_score = kwargs.get('score')
			activity.selected_options = ", ".join(kwargs.get('selected_options'))
			activity.result = ", ".join([str(item) for item in kwargs.get('result')]),
			activity.status = "Passed"
		current_activity.save()
		frappe.db.commit()
	else:
		if content_type in ("Article", "Video"):
			lms_activity_list = [[data.course_name, data.content_name] for data in activity.lms_activity]
			if not [kwargs.get('course'), kwargs.get('content')] in lms_activity_list:
				activity.append("lms_activity", {
					"course_name": kwargs.get('course'),
					"content_name": kwargs.get('content'),
					"status": "Completed"
				})
		else:
			activity.append("lms_activity", {
				"course_name": kwargs.get('course'),
				"content_name": kwargs.get('content'),
				"status": "Passed",
				"quiz_score": kwargs.get('score'),
				"selected_options": ", ".join(kwargs.get('selected_options')),
				"result": ", ".join([str(item) for item in kwargs.get('result')])
			})
		activity.save()
		frappe.db.commit()

def check_entry_exists(program):
	try:
		activity_name = frappe.get_all("Course Activity", filters={"student_id": get_student_id(frappe.session.user), "program_name": program})[0]
	except IndexError:
		return True, None
	else:
		return None, frappe.get_doc("Course Activity", activity_name)

def get_contents_in_course(course_name):
	try:
		course_doc = frappe.get_doc("Course", {"name":course_name, "is_published": True})
		return [frappe.get_doc("Content", content.content) for content in course_doc.get_all_children()]
	except frappe.DoesNotExistError:
		return None

def get_courses_in_program(program):
	try:
		program_doc = frappe.get_doc("Program", program)
		if program_doc.is_published:
			course_list = [frappe.get_doc("Course", course.course_name) for course in program_doc.get_all_children()]
			return [course for course in course_list if course.is_published == True]
		else:
			return None
	except frappe.DoesNotExistError:
		return None

def get_program():
	program_list = frappe.get_list("Program", filters={"is_published": is_published})
	if program_list:
		return program_list
	else:
		return None

def get_featured_programs():
	featured_programs_name = frappe.get_list("Program", filters={"is_published": True, "is_featured": True})
	featured_list = [frappe.get_doc("Program", program["name"]) for program in featured_programs_name]
	if featured_list:
		return featured_list
	else:
		return None

@frappe.whitelist()
def add_course_enrollment(course, email):
	student_id = get_student_id(email)
	if not get_course_enrollment(course, email):
		enrollment = frappe.get_doc({
			"doctype": "Course Enrollment",
			"student": student_id,
			"course": course
		})
		enrollment.save()
		frappe.db.commit()
		return enrollment

def get_course_enrollment(course, email):
	student_id = get_student_id(email)
	try:
		return frappe.get_list("Course Enrollment", filters={'course':course, 'student':student_id})[0]
	except IndexError:
		return None

def get_student_id(email):
	"""Returns Student ID, example EDU-STU-2018-00001 from email address
	
	:params email: email address of the student"""
	try:
		return frappe.get_list('Student', filters={'student_email_id': email})[0].name
	except IndexError:
		frappe.throw("Student Account with email:{0} does not exist".format(email))

def get_quiz(content):
	"""Helper Function to get questions for a quiz
	
	:params content: name of a Content doctype with content_type quiz"""
	try:
		quiz_doc = frappe.get_doc("Content", content)
		if quiz_doc.content_type != "Quiz":
			frappe.throw("<b>{0}</b> is not a Quiz".format(content))
		
		import json
		quiz = [frappe.get_doc("Question", item.question_link) for item in quiz_doc.questions]
		data = []
		for question in quiz:
			d = {}
			d['Question'] = question.question
			d['Options'] = [item.option for item in quiz[0].options]
			data.append(d)
		return data
	except frappe.DoesNotExistError:
		frappe.throw("The quiz \"{0}\" does not exist".format(content))
