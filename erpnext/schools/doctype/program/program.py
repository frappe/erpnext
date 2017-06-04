# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Program(Document):
	def validate(self):
		self.validate_course()
		
	def validate_course(self):
		for d in self.courses:
			if not d.course_code:
				d.course_code = frappe.db.get_value("Course", d.course, "course_code")
