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
	
	def get_contents_based_on_type(self): 
		contents= self.get_contents()
		quiz_list = [item for item in contents if item.doctype=="Quiz"]
		content_list = [item for item in contents if item.doctype!="Quiz"]
		return content_list, quiz_list

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