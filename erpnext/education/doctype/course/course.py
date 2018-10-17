# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class Course(Document):
	def validate(self):
		self.validate_assessment_criteria()

	def validate_assessment_criteria(self):
		if self.assessment_criteria:
			total_weightage = 0
			for criteria in self.assessment_criteria:
				total_weightage += criteria.weightage or 0
			if total_weightage != 100:
				frappe.throw(_("Total Weightage of all Assessment Criteria must be 100%"))

	def get_content_data(self, data):
		try:
			course_content_list = self.get_all_children()
			content_data = [frappe.get_value(course_content.content_type, course_content.content, data) for course_content in course_content_list]
		except Exception as e:
			print(e)
			return None
		return content_data

	def get_content_title(self):
		'''
		returns all the course content for the given course object.
		'''
		content_title = self.get_content_data("title")
		return content_title
