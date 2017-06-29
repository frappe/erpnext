# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from collections import defaultdict

def execute(filters=None):
	args = frappe._dict()
	args["assessment_group"] = filters.get("assessment_group")
	if args["assessment_group"] == "All Assessment Groups":
		frappe.throw(_("Please select the assessment group other than 'All Assessment Groups'"))

	args["course"] = filters.get("course")
	args["student_group"] = filters.get("student_group")
	if args["student_group"]:
		cond = "and ap.student_group=%(student_group)s"
	else:
		cond = ''

	# find all assessment plan linked with the filters provided
	assessment_plan = frappe.db.sql('''
		select
			ap.name, ap.student_group, apc.assessment_criteria, apc.maximum_score as max_score
		from
			`tabAssessment Plan` ap, `tabAssessment Plan Criteria` apc
		where
			ap.assessment_group=%(assessment_group)s and ap.course=%(course)s and
			ap.name=apc.parent and ap.docstatus=1 {0}
		order by
			apc.assessment_criteria'''.format(cond), (args), as_dict=1)

	assessment_plan_list = set([d["name"] for d in assessment_plan])
	if not assessment_plan_list:
		frappe.throw(_("No assessment plan linked with this assessment group"))

	student_group_list = set([d["student_group"] for d in assessment_plan])
	assessment_result = frappe.db.sql('''select ar.student, ard.assessment_criteria, ard.grade, ard.score
		from `tabAssessment Result` ar, `tabAssessment Result Detail` ard
		where ar.assessment_plan in (%s) and ar.name=ard.parent and ar.docstatus=1
		order by ard.assessment_criteria''' %', '.join(['%s']*len(assessment_plan_list)),
		tuple(assessment_plan_list), as_dict=1)

	result_dict = defaultdict(dict)
	kounter = defaultdict(dict)
	for result in assessment_result:
		result_dict[result.student].update({frappe.scrub(result.assessment_criteria): result.grade,
			frappe.scrub(result.assessment_criteria)+"_score": result.score})
		if result.grade in kounter[result.assessment_criteria]:
			kounter[result.assessment_criteria][result.grade] += 1
		else:
			kounter[result.assessment_criteria].update({result.grade: 1})

	student_list = frappe.db.sql('''select sgs.student, sgs.student_name
		from `tabStudent Group` sg, `tabStudent Group Student` sgs
		where sg.name = sgs.parent and sg.name in (%s)
		order by sgs.group_roll_number asc''' %', '.join(['%s']*len(student_group_list)),
		tuple(student_group_list), as_dict=1)

	for student in student_list:
		student.update(result_dict[student.student])
	data = student_list

	columns = get_column(list(set([(d["assessment_criteria"],d["max_score"]) for d in assessment_plan])))

	grading_scale = frappe.db.get_value("Assessment Plan", list(assessment_plan_list)[0], "grading_scale")
	grades = frappe.db.sql_list('''select grade_code from `tabGrading Scale Interval` where parent=%s''',
		(grading_scale))
	assessment_criteria_list = list(set([d["assessment_criteria"] for d in assessment_plan]))
	chart = get_chart_data(grades, assessment_criteria_list, kounter)

	return columns, data, None, chart

def get_column(assessment_criteria):
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
	for d in assessment_criteria:
		columns.append({
			"fieldname": frappe.scrub(d[0]),
			"label": d[0],
			"fieldtype": "Data",
			"width": 110
		})
		columns.append({
			"fieldname": frappe.scrub(d[0]) +"_score",
			"label": "Score(" + str(int(d[1])) + ")",
			"fieldtype": "Float",
			"width": 100
		})
	return columns

def get_chart_data(grades, assessment_criteria_list, kounter):
	grades = sorted(grades)
	chart_data = []
	chart_data.append(["x"] + assessment_criteria_list)
	for grade in grades:
		tmp = [grade]
		for ac in assessment_criteria_list:
			if grade in kounter[ac]:
				tmp.append(kounter[ac][grade])
			else:
				tmp.append(0)
		chart_data.append(tmp)
	return {
		"data": {
			"x": "x",
			"columns": chart_data
		},
		"chart_type": 'bar',
	}
