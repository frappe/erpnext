# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestTopic(unittest.TestCase):
	def setUp(self):
		make_topic_and_linked_content("_Test Topic 1", [{"type":"Article", "name": "_Test Article 1"}])

	def test_get_contents(self):
		topic = frappe.get_doc("Topic", "_Test Topic 1")
		contents = topic.get_contents()
		self.assertEqual(contents[0].doctype, "Article")
		self.assertEqual(contents[0].name, "_Test Article 1")
		frappe.db.rollback()

def make_topic(name):
	try:
		topic = frappe.get_doc("Topic", name)
	except frappe.DoesNotExistError:
		topic = frappe.get_doc({
			"doctype": "Topic",
			"topic_name": name,
			"topic_code": name,
		}).insert()
	return topic.name

def make_topic_and_linked_content(topic_name, content_dict_list):
	try:
		topic = frappe.get_doc("Topic", topic_name)
	except frappe.DoesNotExistError:
		make_topic(topic_name)
		topic = frappe.get_doc("Topic", topic_name)
	content_list = [make_content(content['type'], content['name']) for content in content_dict_list]
	for content in content_list:
		topic.append("topic_content", {"content": content.title, "content_type": content.doctype})
	topic.save()
	return topic


def make_content(type, name):
	try:
		content = frappe.get_doc(type, name)
	except frappe.DoesNotExistError:
		content = frappe.get_doc({"doctype": type, "title": name}).insert()
	return content
