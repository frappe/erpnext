# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

from erpnext.education.doctype.topic.test_topic import make_topic_and_linked_content
from erpnext.education.doctype.course.test_course import make_course_and_linked_topic
from erpnext.education.doctype.program.test_program import make_program_and_linked_courses


test_program = frappe._dict({
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
	},
	{
		"course_name": "_Test Course 2",
		"topic": [
		{
			"topic_name": "_Test Topic 2-1",
			"content": [{
				"type": "Article",
				"name": "_Test Article 2-1"
			},{
				"type": "Article",
				"name": "_Test Article 2-2"
			}
			]
		},
		{
			"topic_name": "_Test Topic 2-2",
			"content": [{
				"type": "Article",
				"name": "_Test Article 2-3"
			},{
				"type": "Article",
				"name": "_Test Article 2-4"
			}
			]
		}
		]
	}]
})

class TestCourseActivity(unittest.TestCase):
	def setUp(self):
		pass

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
	topic_list = [course['topic'] for course in test_program['course']]
	for topic in topic_list[0]:
		make_topic_and_linked_content(topic['topic_name'], topic['content'])

	all_courses_list = [{'course': course['course_name'], 'topic': [topic['topic_name'] for topic in course['topic']]} for course in test_program['course']] # returns [{'course': 'Applied Math', 'topic': ['Trignometry', 'Geometry']}]
	for course in all_courses_list:
		make_course_and_linked_topic(course['course'], course['topic'])

	course_list = [course['course_name'] for course in test_program['course']]
	program = make_program_and_linked_courses(test_program.program_name, course_list)
	return program
