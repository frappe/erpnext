# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Program(Document):

	def get_course_list(self):
		course_content_list = self.get_all_children()
		course_list = [frappe.get_doc("Course", course_item.course) for course_item in course_content_list]
		return course_list