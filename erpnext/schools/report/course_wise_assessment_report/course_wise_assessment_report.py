# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from collections import defaultdict

def execute(filters=None):

	assessment_group = filters.get("assessment_group")
	student_group = filters.get("student_group")
	course = frappe.db.get_value("Student Group", student_group, "course")
	if not course:
		frappe.throw(_("Student Group {0} is not linked with any course").format(student_group))

	assessment_plan = frappe.db.sql('''select ap.name, apc.assessment_criteria, apc.maximum_score as max_score
		from `tabAssessment Plan` ap, `tabAssessment Plan Criteria` apc
		where ap.assessment_group=%s and ap.student_group=%s and ap.name=apc.parent and ap.docstatus=1
		order by apc.assessment_criteria''', (assessment_group, student_group), as_dict=1)
	assessment_plan_list = set([d["name"] for d in assessment_plan])

	assessment_result = frappe.db.sql('''select ar.student, ard.assessment_criteria, ard.grade, ard.score 
		from `tabAssessment Result` ar, `tabAssessment Result Detail` ard
		where ar.assessment_plan in (%s) and ar.name=ard.parent and ar.docstatus=1
		order by ard.assessment_criteria''' %', '.join(['%s']*len(assessment_plan_list)), tuple(assessment_plan_list), as_dict=1)

	result_dict = defaultdict(list)
	for result in assessment_result:
		result_dict[result.student].append(result.grade)
		result_dict[result.student].append(result.score)

	student_list = frappe.db.sql('''select sgs.group_roll_number, sgs.student, sgs.student_name 
		from `tabStudent Group` sg, `tabStudent Group Student` sgs
		where sg.name = sgs.parent and sg.name = %s
		order by sgs.group_roll_number asc''', (student_group), as_list=1)

	data = []
	for student in student_list:
		tmp_list = student + result_dict[student[1]]
		data.append(tmp_list)

	return get_column(assessment_plan), data

def get_column(assessment_plan):
	columns = [ 
		_("Group Roll No") + "::80", 
		_("Student ID") + ":Link/Student:90", 
		_("Student Name") + "::160", 
	]
	for d in assessment_plan:
		columns.append(d.get("assessment_criteria") + "::110")
		columns.append("Max Score(" + str(int(d.get("max_score"))) + ")::110")
	return columns
