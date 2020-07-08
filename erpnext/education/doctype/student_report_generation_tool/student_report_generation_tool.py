# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.model.document import Document
from erpnext.education.api import get_grade
from frappe.utils.pdf import get_pdf
from erpnext.education.report.course_wise_assessment_report.course_wise_assessment_report import get_formatted_result
from erpnext.education.report.course_wise_assessment_report.course_wise_assessment_report import get_child_assessment_groups


class StudentReportGenerationTool(Document):
	pass


@frappe.whitelist()
def preview_report_card(doc):
	doc = frappe._dict(json.loads(doc))
	doc.students = [doc.student]
	if not (doc.student_name and doc.student_batch):
		program_enrollment = frappe.get_all("Program Enrollment", fields=["student_batch_name", "student_name"],
			filters={"student": doc.student, "docstatus": ('!=', 2), "academic_year": doc.academic_year})
		if program_enrollment:
			doc.batch = program_enrollment[0].student_batch_name
			doc.student_name = program_enrollment[0].student_name

	# get the assessment result of the selected student
	values = get_formatted_result(doc, get_course=True, get_all_assessment_groups=doc.include_all_assessment)
	assessment_result = values.get("assessment_result").get(doc.student)
	courses = values.get("course_dict")
	course_criteria = get_courses_criteria(courses)

	# get the assessment group as per the user selection
	if doc.include_all_assessment:
		assessment_groups = get_child_assessment_groups(doc.assessment_group)
	else:
		assessment_groups = [doc.assessment_group]

	# get the attendance of the student for that peroid of time.
	doc.attendance = get_attendance_count(doc.students[0], doc.academic_year, doc.academic_term)

	template = "erpnext/education/doctype/student_report_generation_tool/student_report_generation_tool.html"
	base_template_path = "frappe/www/printview.html"

	from frappe.www.printview import get_letter_head
	letterhead = get_letter_head(frappe._dict({"letter_head": doc.letterhead}), not doc.add_letterhead)

	html = frappe.render_template(template,
		{
			"doc": doc,
			"assessment_result": assessment_result,
			"courses": courses,
			"assessment_groups": assessment_groups,
			"course_criteria": course_criteria,
			"letterhead": letterhead and letterhead.get('content', None),
			"add_letterhead": doc.add_letterhead if doc.add_letterhead else 0
		})
	final_template = frappe.render_template(base_template_path, {"body": html, "title": "Report Card"})

	frappe.response.filename = "Report Card " + doc.students[0] + ".pdf"
	frappe.response.filecontent = get_pdf(final_template)
	frappe.response.type = "download"


def get_courses_criteria(courses):
	course_criteria = frappe._dict()
	for course in courses:
		course_criteria[course] = [d.assessment_criteria for d in frappe.get_all("Course Assessment Criteria",
			fields=["assessment_criteria"], filters={"parent": course})]
	return course_criteria


def get_attendance_count(student, academic_year, academic_term=None):
	if academic_year:
		from_date, to_date = frappe.db.get_value("Academic Year", academic_year, ["year_start_date", "year_end_date"])
	elif academic_term:
		from_date, to_date = frappe.db.get_value("Academic Term", academic_term, ["term_start_date", "term_end_date"])
	if from_date and to_date:
		attendance = dict(frappe.db.sql('''select status, count(student) as no_of_days
			from `tabStudent Attendance` where student = %s and docstatus = 1
			and date between %s and %s group by status''',
			(student, from_date, to_date)))
		if "Absent" not in attendance.keys():
			attendance["Absent"] = 0
		if "Present" not in attendance.keys():
			attendance["Present"] = 0
		return attendance
	else:
		frappe.throw(_("Provide the academic year and set the starting and ending date."))
