# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.schools.doctype.student_batch.student_batch import validate_active_student_batch

class CourseSchedule(Document):
	def validate(self):
		self.instructor_name = frappe.db.get_value("Instructor", self.instructor, "instructor_name")
		self.set_title()
		self.validate_mandatory()
		self.validate_course()
		self.set_student_batch()
		self.validate_date()
		self.validate_overlap()
		
		if self.student_batch:
			validate_active_student_batch(self.student_batch)
	
	def set_title(self):
		"""Set document Title"""
		self.title = self.course + " by " + (self.instructor_name if self.instructor_name else self.instructor)

	def validate_mandatory(self):
		if not (self.student_batch or self.student_group):
			frappe.throw(_("""Student Batch or Student Group is mandatory"""))
	
	def validate_course(self):
		if self.student_group:
			self.course= frappe.db.get_value("Student Group", self.student_group, "course")
	
	def set_student_batch(self):
		if self.student_group:
			self.student_batch = frappe.db.get_value("Student Group", self.student_group, "student_batch")
	
	def validate_date(self):
		"""Validates if from_time is greater than to_time"""
		if self.from_time > self.to_time:
			frappe.throw(_("From Time cannot be greater than To Time."))
	
	def validate_overlap(self):
		"""Validates overlap for Student Group/Student Batch, Instructor, Room"""
		
		from erpnext.schools.utils import validate_overlap_for

		#Validate overlapping course schedules.
		if self.student_batch:
			validate_overlap_for(self, "Course Schedule", "student_batch")

		if self.student_group:
			validate_overlap_for(self, "Course Schedule", "student_group")
		
		validate_overlap_for(self, "Course Schedule", "instructor")
		validate_overlap_for(self, "Course Schedule", "room")

		#validate overlapping assessment schedules.
		if self.student_batch:
			validate_overlap_for(self, "Assessment", "student_batch")
		
		if self.student_group:
			validate_overlap_for(self, "Assessment", "student_group")
		
		validate_overlap_for(self, "Assessment", "room")
		validate_overlap_for(self, "Assessment", "supervisor", self.instructor)

