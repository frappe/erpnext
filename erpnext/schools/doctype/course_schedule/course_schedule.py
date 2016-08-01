# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class CourseSchedule(Document):
	def validate(self):
		self.instructor_name = frappe.db.get_value("Instructor", self.instructor, "instructor_name")
		self.set_title()
		self.validate_date()
		self.validate_overlap()
		
	def set_title(self):
		"""Set document Title"""
		self.title = self.course + " by " + (self.instructor_name if self.instructor_name else self.instructor)

	def validate_date(self):
		"""Validates if from_time is greater than to_time"""
		if self.from_time > self.to_time:
			frappe.throw("From Time cannot be greater than To Time.")
	
	def validate_overlap(self):
		"""Validates overlap for Student Group, Instructor, Room"""
		
		from erpnext.schools.utils import validate_overlap_for

		validate_overlap_for(self, "Course Schedule", "student_group" )
		validate_overlap_for(self, "Course Schedule", "instructor")
		validate_overlap_for(self, "Course Schedule", "room")

		validate_overlap_for(self, "Examination", "student_group")
		validate_overlap_for(self, "Examination", "room")
		validate_overlap_for(self, "Examination", "supervisor", self.instructor)

