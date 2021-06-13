	# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.desk.reportview import get_match_cond
class ScheduleSubjectLecture(Document):
	def validate(self):
		self.instructor_name = frappe.db.get_value("Instructor", self.instructor, "instructor_name")
		self.set_title()
		self.validate_course()
		self.validate_date()
		self.validate_overlap()
	
	def set_title(self):
		"""Set document Title"""
		self.title = self.course + " by " + (self.instructor_name if self.instructor_name else self.instructor)
	
	def validate_course(self):
		group_based_on, course = frappe.db.get_value("Student Group", self.student_group, ["group_based_on", "course"])
		if group_based_on == "Course":
			self.course = course

	def validate_date(self):
		"""Validates if from_time is greater than to_time"""
		if self.from_time > self.to_time:
			frappe.throw(_("From Time cannot be greater than To Time."))
	
	def validate_overlap(self):
		"""Validates overlap for Student Group, Instructor, Room"""
		
		from erpnext.education.utils import validate_overlap_for

		#Validate overlapping Schedule Subject Lectures.
		if self.student_group:
			validate_overlap_for(self, "Schedule Subject Lecture", "student_group")
		
		validate_overlap_for(self, "Schedule Subject Lecture", "instructor")
		validate_overlap_for(self, "Schedule Subject Lecture", "room")

		#validate overlapping assessment schedules.
		if self.student_group:
			validate_overlap_for(self, "Assessment Plan", "student_group")
		
		validate_overlap_for(self, "Assessment Plan", "room")
		validate_overlap_for(self, "Assessment Plan", "supervisor", self.instructor)

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_subjects(doctype, txt, searchfield, start, page_len, filters):
	student_group_doc = frappe.get_doc('Student Group',filters['group_name'])
	if student_group_doc.program_and_stream:
		subject_list = frappe.db.sql("""
			SELECT s.name, s.subject_name 
    		 FROM 
    			`tabStudent Group` as sg 
    		JOIN 
				`tabProgram Stream Semester Wise Syllabus` as ps
     			ON ps.program_and_stream = sg.program_and_stream
     		JOIN 
				 `tabsubjects` as sub
     			ON sub.parent = ps.name
			JOIN 
				`tabSubject` as s
				ON s.name = sub.subject
     		WHERE
		 		sg.name = %(groupname)s 
		 		AND
     			SUBSTRING(sg.academic_term,LENGTH(sg.academic_term),LENGTH(sg.academic_term)) = ps.semester 
				AND 
				s.subject_name like %(txt)s
				limit %(start)s, %(page_len)s
		 """.format(**{
            'key': searchfield,
            'mcond':get_match_cond(doctype)
        }),
    		{ 
			'txt': "%s%%" % txt,
            '_txt': txt.replace("%", ""),
            'start': start,
            'page_len': page_len,
			'groupname' : filters['group_name']
		})
	else:
		frappe.throw('Please Select Student Group')
	
	return subject_list

