# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.website.utils import get_comment_list

def get_context(context):
	context.doc = frappe.get_doc('Discussion', frappe.form_dict.discussion)
	portal_items = [{'reference_doctype': u'Topic', 'route': u"/topic?course=" + str(context.doc.course), 'show_always': 0L, 'title': u'Topics'},
				{'reference_doctype': u'Discussion', 'route': u"/discussion?course=" + str(context.doc.course), 'show_always': 0L, 'title': u'Discussions'},

	]
	context.show_sidebar = True
	context.sidebar_items = portal_items
	context.no_cache = 1
	context.doc.has_permission('read')
	context.sidebar_title = context.doc.course
	context.reference_doctype = "Discussion"
	context.reference_name = context.doc.name
	context.comment_list = get_comment_list(context.doc.doctype,context.doc.name)