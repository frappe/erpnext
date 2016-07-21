# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import frappe
from frappe import _

class Examination(Document):
	def validate(self):
		self.validate_overlap()
	
	def validate_overlap(self):
		"""Validates overlap for Student Group, Supervisor, Room"""

		from erpnext.schools.utils import validate_overlap_for

		validate_overlap_for(self, "Examination", "student_group")
		validate_overlap_for(self, "Course Schedule", "student_group" )
		
		if self.room:
			validate_overlap_for(self, "Examination", "room")
			validate_overlap_for(self, "Course Schedule", "room")

		if self.supervisor:
			validate_overlap_for(self, "Examination", "supervisor")
			validate_overlap_for(self, "Course Schedule", "instructor", self.supervisor)

def get_examination_list(doctype, txt, filters, limit_start, limit_page_length=20):
	user = frappe.session.user
	student = frappe.db.sql("select name from `tabStudent` where student_email_id= %s", user)
	if student:
		return frappe. db.sql('''select course, schedule_date, from_time, to_time, sgs.name from `tabExamination` as exam, 
			`tabStudent Group Student` as sgs where exam.student_group = sgs.parent and sgs.student = %s and exam.docstatus=1
			order by exam.name asc limit {0} , {1}'''
			.format(limit_start, limit_page_length), student, as_dict = True)

def get_list_context(context=None):
	return {
		"show_sidebar": True,
		'no_breadcrumbs': True,
		"title": _("Examination Schedule"),
		"get_list": get_examination_list,
		"row_template": "templates/includes/examination/examination_row.html"
	}
