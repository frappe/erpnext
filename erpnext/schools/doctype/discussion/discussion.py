# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class Discussion(Document):
	def validate(self):
		if not self.owner== frappe.session.user:
			frappe.throw(_("Not Permitted"))

def get_discussions(doctype, txt, filters, limit_start, limit_page_length=20):
	from frappe.www.list import get_list
	if not filters:
		filters = []
		filters.append(("Discussion", "course", "=", frappe.form_dict.course))
	return get_list(doctype, txt, filters, limit_start, limit_page_length, ignore_permissions=True)

def get_list_context(context=None):
	course_name = frappe.form_dict.course
	portal_items = [{'reference_doctype': u'Topic', 'route': u"/topic?course=" + str(course_name), 'show_always': 0L, 'title': u'Topics'},
				{'reference_doctype': u'Discussion', 'route': u"/discussion?course=" + str(course_name), 'show_always': 0L, 'title': u'Discussions'},

	]
	sidebar_title = course_name
	return {
		"show_sidebar": True,
		'no_breadcrumbs': True,
		"get_list" : get_discussions,
		"title": _("Discussions"),
		"sidebar_items" : portal_items,
		"sidebar_title" : sidebar_title,
		"row_template": "templates/includes/discussion/discussion_row.html"
	}