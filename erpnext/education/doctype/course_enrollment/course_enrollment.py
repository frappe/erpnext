# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from functools import reduce

class CourseEnrollment(Document):
	def get_progress(self, student):
		"""
		Returns Progress of given student for a particular course enrollment

			:param self: Course Enrollment Object
			:param student: Student Object
		"""
		course = frappe.get_doc('Course', self.course)
		topics = course.get_topics()
		progress = []
		for topic in topics:
				progress.append(student.get_topic_progress(self.name, topic))
		return reduce(lambda x,y: x+y, progress) # Flatten out the List