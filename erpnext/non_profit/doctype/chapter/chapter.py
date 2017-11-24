# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.website.website_generator import WebsiteGenerator
from frappe.model.document import Document
from frappe import _

class Chapter(WebsiteGenerator):
	def get_context(self, context):
		context.no_cache = True

	def validate(self):
		chapter_head = self.chapter_head
		chapter = frappe.get_all('Chapter', filters={'published': True}, fields=['chapter_head'])
		if not self.route:		#pylint: disable=E0203
			self.route = 'chapter/' + self.scrub(self.name)

	def enable(self):
		chapter = frappe.get_doc('Chapter', frappe.form_dict.name)
		chapter.append('members', dict(enable=self.value))
		chapter.save(ignore_permissions=1)
		frappe.db.commit()


def get_list_context(context):
	context.allow_guest = True
	context.no_cache = True
	context.title = 'All Chapters'
	context.no_breadcrumbs = True
	context.order_by = 'creation desc'
	context.introduction = '<p>All Chapters</p>'
