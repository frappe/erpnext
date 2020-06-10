# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and Contributors
# See license.txt
from __future__ import unicode_literals
from erpnext.education.doctype.topic.test_topic import make_topic
from erpnext.education.doctype.topic.test_topic import make_topic_and_linked_content

import frappe
import unittest

# test_records = frappe.get_test_records('Course')

class TestCourse(unittest.TestCase):
	def setUp(self):
		make_topic_and_linked_content("_Test Topic 1", [{"type":"Article", "name": "_Test Article 1"}])
		make_topic_and_linked_content("_Test Topic 2", [{"type":"Article", "name": "_Test Article 2"}])
		make_course_and_linked_topic("_Test Course 1", ["_Test Topic 1", "_Test Topic 2"])

	def test_get_topics(self):
		course = frappe.get_doc("Course", "_Test Course 1")
		topics = course.get_topics()
		self.assertEqual(topics[0].name, "_Test Topic 1")
		self.assertEqual(topics[1].name, "_Test Topic 2")
		frappe.db.rollback()

def make_course(name):
	try:
		course = frappe.get_doc("Course", name)
	except frappe.DoesNotExistError:
		course = frappe.get_doc({
			"doctype": "Course",
			"course_name": name,
			"course_code": name
		}).insert()
	return course.name

def make_course_and_linked_topic(course_name, topic_name_list):
	try:
		course = frappe.get_doc("Course", course_name)
	except frappe.DoesNotExistError:
		make_course(course_name)
		course = frappe.get_doc("Course", course_name)
	topic_list = [make_topic(topic_name) for topic_name in topic_name_list]
	for topic in topic_list:
		course.append("topics", {"topic": topic})
	course.save()
	return course
