# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json

import frappe
from frappe import _
from frappe.model.document import Document


class Topic(Document):
	def get_contents(self):
		try:
			topic_content_list = self.topic_content
			content_data = [frappe.get_doc(topic_content.content_type, topic_content.content) for topic_content in topic_content_list]
		except Exception as e:
			frappe.log_error(frappe.get_traceback())
			return None
		return content_data

@frappe.whitelist()
def get_courses_without_topic(topic):
	data = []
	for entry in frappe.db.get_all('Course'):
		course = frappe.get_doc('Course', entry.name)
		topics = [t.topic for t in course.topics]
		if not topics or topic not in topics:
			data.append(course.name)
	return data

@frappe.whitelist()
def add_topic_to_courses(topic, courses, mandatory=False):
	courses = json.loads(courses)
	for entry in courses:
		course = frappe.get_doc('Course', entry)
		course.append('topics', {
			'topic': topic,
			'topic_name': topic
		})
		course.flags.ignore_mandatory = True
		course.save()
	frappe.db.commit()
	frappe.msgprint(_('Topic {0} has been added to all the selected courses successfully.').format(frappe.bold(topic)),
		title=_('Courses updated'), indicator='green')

@frappe.whitelist()
def add_content_to_topics(content_type, content, topics):
	topics = json.loads(topics)
	for entry in topics:
		topic = frappe.get_doc('Topic', entry)
		topic.append('topic_content', {
			'content_type': content_type,
			'content': content,
		})
		topic.flags.ignore_mandatory = True
		topic.save()
	frappe.db.commit()
	frappe.msgprint(_('{0} {1} has been added to all the selected topics successfully.').format(content_type, frappe.bold(content)),
		title=_('Topics updated'), indicator='green')
