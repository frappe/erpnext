# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import frappe
from frappe import _

class Assessment(Document):
	def validate(self):
		self.validate_overlap()
	
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


def get_assessment_list(doctype, txt, filters, limit_start, limit_page_length=20):
	user = frappe.session.user
	student = frappe.db.sql("select name from `tabStudent` where student_email_id= %s", user)
	if student:
		return frappe. db.sql('''select course, schedule_date, from_time, to_time, sgs.name from `tabAssessment` as assessment, 
			`tabStudent Group Student` as sgs where assessment.student_group = sgs.parent and sgs.student = %s and assessment.docstatus=1
			order by assessment.name asc limit {0} , {1}'''
			.format(limit_start, limit_page_length), student, as_dict = True)

def get_list_context(context=None):
	return {
		"show_sidebar": True,
		'no_breadcrumbs': True,
		"title": _("Assessment Schedule"),
		"get_list": get_assessment_list,
		"row_template": "templates/includes/assessment/assessment_row.html"
	}

@frappe.whitelist()
def get_grade(grading_structure, result):
	grade = frappe.db.sql("""select gi.from_score, gi.to_score, gi.grade_code, gi.grade_description 
		from `tabGrading Structure` as gs, `tabGrade Interval` as gi 
		where gs.name = gi.parent and gs.name = %(grading_structure)s and gi.from_score <= %(result)s 
		and gi.to_score >= %(result)s""".format(), 
		{
			"grading_structure":grading_structure,
			"result": result
		},
		as_dict=True)
   	 
	return grade[0].grade_code if grade else ""

def validate_grade(score, grade):
	pass