# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from collections import defaultdict

def execute(filters=None):
	print "======================================"

	assessment_group = filters.get("assessment_group")
	student_group = filters.get("student_group")

	if student_group:
		course = frappe.db.get_value("Student Group", student_group, "course")
		if not course:
			frappe.throw(_("Student Group {0} is not linked with any course").format(student_group))
		# student_group_list = [student_group]
	else:
		course = filters.get("course")
		if not course:
			frappe.throw(_("Please select Student Group or Course"))
		# student_group_list = frappe.get_list("Student Group", fields=["name"], filters={"program":program, "course":course})

	# find assessment plan according to the student group list
	assessment_plan = frappe.db.sql('''select ap.name, ap.student_group, apc.assessment_criteria, apc.maximum_score as max_score
		from `tabAssessment Plan` ap, `tabAssessment Plan Criteria` apc
		where ap.assessment_group=%s and ap.course=%s and ap.name=apc.parent and ap.docstatus=1
		order by apc.assessment_criteria''', (assessment_group, course), as_dict=1)
	print assessment_plan
	assessment_plan_list = set([d["name"] for d in assessment_plan])
	student_group_list = set([d["student_group"] for d in assessment_plan])
	assessment_criteria_list = set([(d["assessment_criteria"],d["max_score"]) for d in assessment_plan])
	assessment_plan
	if not assessment_plan_list:
		frappe.throw(_("No assessment plan linked with this assessment group"))

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
		where sg.name = sgs.parent and sg.name in (%s)
		order by sgs.group_roll_number asc''' %', '.join(['%s']*len(student_group_list)), tuple(student_group_list), as_list=1)

	data = []
	for student in student_list:
		tmp_list = student + result_dict[student[1]]
		data.append(tmp_list)

	return get_column(assessment_criteria_list), data

def get_column(assessment_criteria):
	columns = [ 
		_("Batch Roll No") + "::60", 
		_("Student ID") + ":Link/Student:90", 
		_("Student Name") + "::160", 
	]
	for d in assessment_criteria:
		columns.append(d[0] + "::110")
		columns.append("Score(" + str(int(d[1])) + ")::100")
	return columns
