# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class Topic(Document):
	pass

def get_topic_list(doctype, txt, filters, limit_start, limit_page_length=20):
	user = frappe.session.user
	student = frappe.db.sql("select name from `tabStudent` where student_email_id= %s", user)
	if student:
		data = frappe. db.sql('''select name, course, modified,topic_name, introduction, content from `tabTopic` as topic
								where topic.course = %s 
								order by idx asc limit {0} , {1}'''.format(limit_start, limit_page_length),filters.course,as_dict = True)
		
		for topic in data:
			try:
				num_attachments = frappe.db.sql(""" select count(file_url) from tabFile as file
													where file.attached_to_name=%s 
													and file.attached_to_doctype=%s""",(topic.name,"Topic"))

			except IOError or frappe.DoesNotExistError:
				pass
				frappe.local.message_log.pop()

			topic.num_attachments = num_attachments[0][0]

		return data

def get_list_context(context=None):
	course = frappe.get_doc('Course', frappe.form_dict.course)
	portal_items = [{'reference_doctype': u'Topic', 'route': u"/topic?course=" + str(course.name), 'show_always': 0L, 'title': u'Topics'},
				{'reference_doctype': u'Discussion', 'route': u"/discussion?course=" + str(course.name), 'show_always': 0L, 'title': u'Discussions'},

	]
	return {
		"show_sidebar": True,
		"title": _("Topic"),
		'no_breadcrumbs': True,
		"sidebar_items" : portal_items,
		"sidebar_title" : course.name,
		"get_list": get_topic_list,
		"row_template": "templates/includes/topic/topic_row.html"
	}