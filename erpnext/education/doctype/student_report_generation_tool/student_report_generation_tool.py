# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext.education.api import get_grade
from frappe.utils.pdf import get_pdf
from erpnext.education.report.course_wise_assessment_report.course_wise_assessment_report import get_formatted_result
from erpnext.education.report.course_wise_assessment_report.course_wise_assessment_report import get_child_assessment_groups


class StudentReportGenerationTool(Document):
	pass


@frappe.whitelist()
def preview_report_card(program, assessment_group, academic_year, academic_term=None, student=None, student_group=None,
		max_days=None, present_days=None, parents_meeting=None, parents_attendance=None):
	doc = frappe._dict()

	# doc.program = program
	doc.assessment_group = assessment_group
	doc.academic_year = academic_year
	doc.max_days = max_days
	doc.present_days = present_days
	doc.parents_meeting = parents_meeting
	doc.parents_attendance = parents_attendance
	if academic_term:
		doc.academic_term = academic_term
	if student_group:
		doc.student_group = student_group
	if student:
		doc.students = [student]

	if not doc.students and not doc.student_group:
		frappe.throw("Please select the Student or Student Group")

	values = get_formatted_result(doc, get_course=True, get_all_assessment_groups=True)
	student_details = values.get("student_details")
	assessment_result = values.get("assessment_result").get(doc.students[0])
	courses = values.get("course_dict")
	course_criteria = get_courses_criteria(courses)
	assessment_groups = get_child_assessment_groups(doc.assessment_group)

	if program:
		doc.program = program
	template = "erpnext/education/doctype/student_report_generation_tool/student_report_generation_tool.html"
	base_template_path = "frappe/www/printview.html"
	
	html = frappe.render_template(template,
		{
			"doc": doc,
			"assessment_result": assessment_result,
			"courses": courses,
			"assessment_groups": assessment_groups,
			"course_criteria": course_criteria
		})

	final_template = frappe.render_template(base_template_path, {
		"body": html,
		"title": "Report Card"
	})

	frappe.response.filename = "Report Card.pdf"
	frappe.response.filecontent = get_pdf(final_template)
	frappe.response.type = "download"

def get_courses_criteria(courses):
	course_criteria = frappe._dict()
	for course in courses:
		course_criteria[course] = [d.assessment_criteria for d in frappe.get_all("Course Assessment Criteria",
			fields=["assessment_criteria"], filters={"parent": course})]
	return course_criteria
