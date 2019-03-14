# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

from erpnext.education.doctype.topic.test_topic import make_topic_and_linked_content
from erpnext.education.doctype.course.test_course import make_course_and_linked_topic
from erpnext.education.doctype.program.test_program import make_program_and_linked_courses

from erpnext.education.doctype.student.test_student import create_student
from erpnext.education.doctype.student.test_student import get_student

test_data = frappe._dict({
	"program_name": "_Test Program",
	"course": [{
		"course_name": "_Test Course 1",
		"topic": [
		{
			"topic_name": "_Test Topic 1-1",
			"content": [{
				"type": "Article",
				"name": "_Test Article 1-1"
			},{
				"type": "Article",
				"name": "_Test Article 1-2"
			}
			]
		},
		{
			"topic_name": "_Test Topic 1-2",
			"content": [{
				"type": "Article",
				"name": "_Test Article 1-3"
			},{
				"type": "Article",
				"name": "_Test Article 1-4"
			}
			]
		}
		]
	}]
})

class TestCourseEnrollment(unittest.TestCase):
	def setUp(self):
		setup_program()
		student = create_student({"first_name": "_Test First", "last_name": "_Test Last", "email": "_test_student_1@example.com"})
		program_enrollment = student.enroll_in_program("_Test Program")
		course_enrollment = student.enroll_in_course("_Test Course 1", program_enrollment.name)
		make_course_activity(course_enrollment.name, "Article", "_Test Article 1-1")

	def test_get_progress(self):
		student = get_student("_test_student_1@example.com")
		program_enrollment_name = frappe.get_list("Program Enrollment", filters={"student": student.name, "Program": "_Test Program"})[0].name
		course_enrollment_name = frappe.get_list("Course Enrollment", filters={"student": student.name, "course": "_Test Course 1", "program_enrollment": program_enrollment_name})[0].name
		course_enrollment = frappe.get_doc("Course Enrollment", course_enrollment_name)
		progress = course_enrollment.get_progress(student)
		finished = {'content': '_Test Article 1-1', 'content_type': 'Article', 'is_complete': True}
		self.assertTrue(finished in progress)


def make_course_activity(enrollment, content_type, content):
	activity = frappe.get_all("Course Activity", filters={'enrollment': enrollment, 'content_type': content_type, 'content': content})
	try:
		activity = frappe.get_doc("Course Activity", activity[0]['name'])
	except (IndexError, frappe.DoesNotExistError):
		activity = frappe.get_doc({
			"doctype": "Course Activity",
			"enrollment": enrollment,
			"content_type": content_type,
			"content": content,
			"activity_date": frappe.utils.datetime.datetime.now()
		}).insert()
	return activity

def setup_program():
	topic_list = [course['topic'] for course in test_data['course']]
	for topic in topic_list[0]:
		make_topic_and_linked_content(topic['topic_name'], topic['content'])

	all_courses_list = [{'course': course['course_name'], 'topic': [topic['topic_name'] for topic in course['topic']]} for course in test_data['course']] # returns [{'course': 'Applied Math', 'topic': ['Trignometry', 'Geometry']}]
	for course in all_courses_list:
		make_course_and_linked_topic(course['course'], course['topic'])

	course_list = [course['course_name'] for course in test_data['course']]
	program = make_program_and_linked_courses(test_data.program_name, course_list)
	return program
