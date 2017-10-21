# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from collections import defaultdict
from erpnext.schools.api import get_grade


def execute(filters=None):
	data = []

	args = frappe._dict()
	args["assessment_group"] = filters.get("assessment_group")
	if args["assessment_group"] == "All Assessment Groups":
		frappe.throw(_("Please select the assessment group other than 'All Assessment Groups'"))

	args["course"] = filters.get("course")
	args["student_group"] = filters.get("student_group")


	# find all assessment plan and related details linked with the given filters
	def get_assessment_details():
		if args["student_group"]:
			cond = "and ap.student_group=%(student_group)s"
		else:
			cond = ''

		assessment_plan = frappe.db.sql('''
			select
				ap.name, ap.student_group, ap.grading_scale, apc.assessment_criteria, apc.maximum_score as max_score
			from
				`tabAssessment Plan` ap, `tabAssessment Plan Criteria` apc
			where
				ap.assessment_group=%(assessment_group)s and ap.course=%(course)s and
				ap.name=apc.parent and ap.docstatus=1 {0}
			order by
				apc.assessment_criteria'''.format(cond), (args), as_dict=1)

		assessment_plan_list = list(set([d["name"] for d in assessment_plan]))
		if not assessment_plan_list:
			frappe.throw(_("No assessment plan linked with this assessment group"))

		assessment_criteria_list = list(set([(d["assessment_criteria"],d["max_score"]) for d in assessment_plan]))
		student_group_list = list(set([d["student_group"] for d in assessment_plan]))
		total_maximum_score = flt(sum([flt(d[1]) for d in assessment_criteria_list]))
		grading_scale = assessment_plan[0]["grading_scale"]

		return assessment_plan_list, assessment_criteria_list, total_maximum_score, grading_scale, student_group_list


	# get all the result and make a dict map student as the key and value as dict of result
	def get_result_map():
		result_dict = defaultdict(dict)
		kounter = defaultdict(dict)
		assessment_result = frappe.db.sql('''select ar.student, ard.assessment_criteria, ard.grade, ard.score
			from `tabAssessment Result` ar, `tabAssessment Result Detail` ard
			where ar.assessment_plan in (%s) and ar.name=ard.parent and ar.docstatus=1
			order by ard.assessment_criteria''' %', '.join(['%s']*len(assessment_plan_list)),
			tuple(assessment_plan_list), as_dict=1)

		for result in assessment_result:
			if "total_score" in result_dict[result.student]:
				total_score = result_dict[result.student]["total_score"] + result.score
			else:
				total_score = result.score
			total = get_grade(grading_scale, (total_score/total_maximum_score)*100)

			if result.grade in kounter[result.assessment_criteria]:
				kounter[result.assessment_criteria][result.grade] += 1
			else:
				kounter[result.assessment_criteria].update({result.grade: 1})

			if "Total" not in kounter:
				kounter["Total"] = {}

			if "total" in result_dict[result.student]:
				prev_grade = result_dict[result.student]["total"]
				prev_grade_count = kounter["Total"].get(prev_grade) - 1
				kounter["Total"].update({prev_grade: prev_grade_count})
			latest_grade_count = kounter["Total"].get(total)+1 if kounter["Total"].get(total) else 1
			kounter["Total"].update({total: latest_grade_count})

			result_dict[result.student].update({
					frappe.scrub(result.assessment_criteria): result.grade,
					frappe.scrub(result.assessment_criteria)+"_score": result.score,
					"total_score": total_score,
					"total": total
				})

		return result_dict, kounter

	# make data from the result dict
	def get_data():
		student_list = frappe.db.sql('''select sgs.student, sgs.student_name
			from `tabStudent Group` sg, `tabStudent Group Student` sgs
			where sg.name = sgs.parent and sg.name in (%s)
			order by sgs.group_roll_number asc''' %', '.join(['%s']*len(student_group_list)),
			tuple(student_group_list), as_dict=1)

		for student in student_list:
			student.update(result_dict[student.student])
		return student_list


	# get chart data
	def get_chart():
		grading_scale = frappe.db.get_value("Assessment Plan", list(assessment_plan_list)[0], "grading_scale")
		grades = frappe.db.sql_list('''select grade_code from `tabGrading Scale Interval` where parent=%s''',
			(grading_scale))
		criteria_list = [d[0] for d in assessment_criteria_list] + ["Total"]
		return get_chart_data(grades, criteria_list, kounter)


	assessment_plan_list, assessment_criteria_list, total_maximum_score, grading_scale,\
		student_group_list = get_assessment_details()
	result_dict, kounter = get_result_map()
	data = get_data()

	columns = get_column(assessment_criteria_list, total_maximum_score)
	chart = get_chart()
	data_to_be_printed = [{
		"assessment_plan": ", ".join(assessment_plan_list)
	}]

	return columns, data, None, chart, data_to_be_printed

def get_column(assessment_criteria, total_maximum_score):
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

	columns += [{
		"fieldname": "total",
		"label": "Total",
		"fieldtype": "Data",
		"width": 100
	},
	{
		"fieldname": "total_score",
		"label": "Total Score("+ str(int(total_maximum_score)) + ")",
		"fieldtype": "Float",
		"width": 110
	}]

	return columns

def get_chart_data(grades, assessment_criteria_list, kounter):
	grades = sorted(grades)
	datasets = []
	for grade in grades:
		tmp = []
		for ac in assessment_criteria_list:
			if grade in kounter[ac]:
				tmp.append(kounter[ac][grade])
			else:
				tmp.append(0)
		datasets.append(tmp)
	return {
		"data": {
			"labels": assessment_criteria_list,
			"datasets": datasets
		},
		"type": 'bar',
	}
