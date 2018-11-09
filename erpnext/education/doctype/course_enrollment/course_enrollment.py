# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class CourseEnrollment(Document):
	
	def get_linked_activity(self):
		course_activity_list = frappe.get_all("Course Activity", filters={'enrollment':self.name})
		course_activity = [frappe.get_doc("Course Activity", activity.name) for activity in course_activity_list] 
		quiz_activity_list = frappe.get_all("Quiz Activity", filters={'enrollment':self.name})
		quiz_activity = [frappe.get_doc("Quiz Activity", activity.name) for activity in quiz_activity_list] 
		return course_activity, quiz_activity

	def get_all_activity(self):
		courses, quizes = self.get_linked_activity()
		joined = courses + quizes
		activity = sorted(joined, key = lambda i: i.modified) # Sorting based on modified timestamp
		return activity
		
	def check_course_completion(self):
		pass

	def get_last_activity(self):
		if len(self.get_all_activity()) == 0:
			return None
		else:
			return self.get_all_activity()[-1]