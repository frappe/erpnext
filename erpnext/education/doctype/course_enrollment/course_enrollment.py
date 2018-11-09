# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class CourseEnrollment(Document):
	
	def get_all_activity(self):
		course_activity_list = frappe.get_all("Course Activity", filters={'enrollment':self.name}, fields=['content', 'content_type', 'modified'], order_by='modified')
		quiz_activity_list = frappe.get_all("Quiz Activity", filters={'enrollment':self.name}, fields=['quiz', 'status', 'modified'], order_by='modified')
		return course_activity_list, quiz_activity_list