# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Program(Document):

	def get_course_list(self):
		program_course_list = self.get_all_children()
		course_list = [frappe.get_doc("Course", program_course.course) for program_course in program_course_list]
		return course_list