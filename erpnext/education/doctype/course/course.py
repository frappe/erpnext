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

	def get_topics(self):
		try:
			topic_list = self.get_all_children()
			topic_data = [frappe.get_doc("Topic", topic.topic) for topic in topic_list]
		except frappe.DoesNotExistError:
			return None
		return topic_data

	def get_contents(self):
		try:
			topics = self.get_topics()
			content_data = [{'name':topic.name, 'topic_name': topic.topic_name ,'content':topic.get_contents()} for topic in topics]
		except Exception as e:
			return None
		return content_data

	def get_first_content(self):
		return self.get_contents()[0]

	def get_last_content(self):
		return self.get_contents()[-1]