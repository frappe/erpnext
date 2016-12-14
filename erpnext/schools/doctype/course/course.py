# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class Course(Document):
	def validate(self):
		self.validate_evaluation_criterias()
	
	def validate_evaluation_criterias(self):
		if self.evaluation_criterias:
			total_weightage = 0
			for criteria in self.evaluation_criterias:
				total_weightage += criteria.weightage
			if total_weightage != 100:
				frappe.throw(_("Total Weightage of all Evaluation Criterias must be 100%"))

def get_sg_list(doctype, txt, filters, limit_start, limit_page_length=20):
	user = frappe.session.user
	student = frappe.db.sql("select name from `tabStudent` where student_email_id= %s", user)
	if student:
		return frappe.db.sql('''select course, academic_term, academic_year, SG.name from `tabStudent Group`
			as SG, `tabStudent Group Student` as SGS where SG.name = SGS.parent and SGS.student = %s
			order by SG.name asc limit {0} , {1}'''.format(limit_start, limit_page_length), student, as_dict=True)

def get_list_context(context=None):
	return {
		"show_sidebar": True,
		'no_breadcrumbs': True,
		"title": _("Courses"),
		"get_list": get_sg_list,
		"row_template": "templates/includes/course/course_row.html"
	}