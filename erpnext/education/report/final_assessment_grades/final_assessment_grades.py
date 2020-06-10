# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from collections import defaultdict

from erpnext.education.report.course_wise_assessment_report.course_wise_assessment_report import get_formatted_result
from erpnext.education.report.course_wise_assessment_report.course_wise_assessment_report import get_chart_data


def execute(filters=None):
	columns, data, grades = [], [], []
	args = frappe._dict()
	course_wise_analysis = defaultdict(dict)

	args["academic_year"] = filters.get("academic_year")
	assessment_group = args["assessment_group"] = filters.get("assessment_group")

	student_group = filters.get("student_group")
	args.students = frappe.db.sql_list("select student from `tabStudent Group Student` where parent=%s", (student_group))

	values = get_formatted_result(args, get_course=True)
	student_details = values.get("student_details")
	assessment_result = values.get("assessment_result")
	course_dict = values.get("course_dict")

	for student in args.students:
		if student_details.get(student):
			student_row = {}
			student_row["student"] = student
			student_row["student_name"] = student_details[student]
			for course in course_dict:
				scrub_course = frappe.scrub(course)
				if assessment_group in assessment_result[student][course]:
					student_row["grade_" + scrub_course] = assessment_result[student][course][assessment_group]["Total Score"]["grade"]
					student_row["score_" + scrub_course] = assessment_result[student][course][assessment_group]["Total Score"]["score"]

					# create the list of possible grades
					if student_row["grade_" + scrub_course] not in grades:
						grades.append(student_row["grade_" + scrub_course])

					# create the dict of for gradewise analysis
					if student_row["grade_" + scrub_course] not in course_wise_analysis[course]:
						course_wise_analysis[course][student_row["grade_" + scrub_course]] = 1
					else:
						course_wise_analysis[course][student_row["grade_" + scrub_course]] += 1

			data.append(student_row)

	course_list = [d for d in course_dict]
	columns = get_column(course_dict)
	chart = get_chart_data(grades, course_list, course_wise_analysis)
	return columns, data, None, chart


def get_column(course_dict):
	columns = [{
		"fieldname": "student",
		"label": _("Student ID"),
		"fieldtype": "Link",
		"options": "Student",
		"width": 90
	},
	{
		"fieldname": "student_name",
		"label": _("Student Name"),
		"fieldtype": "Data",
		"width": 160
	}]
	for course in course_dict:
		columns.append({
			"fieldname": "grade_" + frappe.scrub(course),
			"label": course,
			"fieldtype": "Data",
			"width": 110
		})
		columns.append({
			"fieldname": "score_" + frappe.scrub(course),
			"label": "Score(" + str(course_dict[course]) + ")",
			"fieldtype": "Float",
			"width": 100
		})

	return columns
