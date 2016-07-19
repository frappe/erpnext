# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe



def get_context(context):
	course = frappe.get_doc('Course', frappe.form_dict.course)
	sidebar_title = course.name

	context.no_cache = 1
	context.show_sidebar = True
	course = frappe.get_doc('Course', frappe.form_dict.course)
	course.has_permission('read')
	context.doc = course
	portal_items = [{'reference_doctype': u'Topic', 'route': u"/topic?course=" + str(course.name), 'show_always': 0L, 'title': u'Topics'},
				{'reference_doctype': u'Discussion', 'route': u"/discussion?course=" + str(course.name), 'show_always': 0L, 'title': u'Discussions'},

	]

	context.sidebar_items = portal_items

	context.sidebar_title = sidebar_title

	context.intro = course.course_intro

