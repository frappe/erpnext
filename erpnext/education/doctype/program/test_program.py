# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and Contributors
# See license.txt
from __future__ import unicode_literals
from erpnext.education.doctype.course.test_course import make_course
from erpnext.education.doctype.topic.test_topic import make_topic_and_linked_content
from erpnext.education.doctype.course.test_course import make_course_and_linked_topic

import frappe
import unittest

test_data = {
	"program_name": "_Test Program",
	"description": "_Test Program",
	"course": [{
		"course_name": "_Test Course 1",
		"topic": [{
				"topic_name": "_Test Topic 1-1",
				"content": [{
					"type": "Article",
					"name": "_Test Article 1-1"
				}, {
					"type": "Article",
					"name": "_Test Article 1-2"
				}]
			},
			{
				"topic_name": "_Test Topic 1-2",
				"content": [{
					"type": "Article",
					"name": "_Test Article 1-3"
				}, {
					"type": "Article",
					"name": "_Test Article 1-4"
				}]
			}
		]
	}]
}

class TestProgram(unittest.TestCase):
	def setUp(self):
		make_program_and_linked_courses("_Test Program 1", ["_Test Course 1", "_Test Course 2"])

	def test_get_course_list(self):
		program = frappe.get_doc("Program", "_Test Program 1")
		course = program.get_course_list()
		self.assertEqual(course[0].name, "_Test Course 1")
		self.assertEqual(course[1].name, "_Test Course 2")
		frappe.db.rollback()

	def tearDown(self):
		for dt in ["Program", "Course", "Topic", "Article"]:
			for entry in frappe.get_all(dt):
				frappe.delete_doc(dt, entry.program)

def make_program(name):
	program = frappe.get_doc({
		"doctype": "Program",
		"program_name": name,
		"program_code": name,
		"description": "_test description",
		"is_published": True,
		"is_featured": True,
	}).insert()
	return program.name

def make_program_and_linked_courses(program_name, course_name_list):
	try:
		program = frappe.get_doc("Program", program_name)
	except frappe.DoesNotExistError:
		make_program(program_name)
		program = frappe.get_doc("Program", program_name)
	course_list = [make_course(course_name) for course_name in course_name_list]
	for course in course_list:
		program.append("courses", {"course": course, "required": 1})
	program.save()
	return program

def setup_program():
	topic_list = [course['topic'] for course in test_data['course']]
	for topic in topic_list[0]:
		make_topic_and_linked_content(topic['topic_name'], topic['content'])

	all_courses_list = [{'course': course['course_name'], 'topic': [topic['topic_name'] for topic in course['topic']]} for course in test_data['course']] # returns [{'course': 'Applied Math', 'topic': ['Trignometry', 'Geometry']}]
	for course in all_courses_list:
		make_course_and_linked_topic(course['course'], course['topic'])

	course_list = [course['course_name'] for course in test_data['course']]
	program = make_program_and_linked_courses(test_data['program_name'], course_list)
	return program