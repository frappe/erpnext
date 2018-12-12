# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Topic(Document):
	def get_contents(self):
		try:
			course_content_list = self.get_all_children()
			content_data = [frappe.get_doc(course_content.content_type, course_content.content) for course_content in course_content_list]
		except Exception as e:
			return None
		return content_data

	def get_first_content(self):
		return self.get_contents()[0]

	def get_last_content(self):
		return self.get_contents()[-1]
