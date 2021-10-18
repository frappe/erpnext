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
	context.sidebar_title = sidebar_title
	context.intro = course.course_intro
