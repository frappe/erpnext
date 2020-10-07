# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from collections import defaultdict, OrderedDict
from erpnext.education.api import get_grade


def execute(filters=None):
	data, chart, grades = [], [], []
	args = frappe._dict()
	grade_wise_analysis = defaultdict(dict)

	args["academic_year"] = filters.get("academic_year")
	args["course"] = filters.get("course")
	args["assessment_group"] = filters.get("assessment_group")

	args["academic_term"] = filters.get("academic_term")
	args["student_group"] = filters.get("student_group")

	if args["assessment_group"] == "All Assessment Groups":
		frappe.throw(_("Please select the assessment group other than 'All Assessment Groups'"))

	returned_values = get_formatted_result(args, get_assessment_criteria=True)
	student_dict = returned_values["student_details"]
	result_dict = returned_values["assessment_result"]
	assessment_criteria_dict = returned_values["assessment_criteria"]

	for student in result_dict:
		student_row = {}
		student_row["student"] = student
		student_row["student_name"] = student_dict[student]
		for criteria in assessment_criteria_dict:
			scrub_criteria = frappe.scrub(criteria)
			if criteria in result_dict[student][args.course][args.assessment_group]:
				student_row[scrub_criteria] = result_dict[student][args.course][args.assessment_group][criteria]["grade"]
				student_row[scrub_criteria + "_score"] = result_dict[student][args.course][args.assessment_group][criteria]["score"]

				# create the list of possible grades
				if student_row[scrub_criteria] not in grades:
					grades.append(student_row[scrub_criteria])

				# create the dict of for gradewise analysis
				if student_row[scrub_criteria] not in grade_wise_analysis[criteria]:
					grade_wise_analysis[criteria][student_row[scrub_criteria]] = 1
				else:
					grade_wise_analysis[criteria][student_row[scrub_criteria]] += 1
			else:
				student_row[frappe.scrub(criteria)] = ""
				student_row[frappe.scrub(criteria)+ "_score"] = ""
		data.append(student_row)

	assessment_criteria_list = [d for d in assessment_criteria_dict]
	columns = get_column(assessment_criteria_dict)
	chart = get_chart_data(grades, assessment_criteria_list, grade_wise_analysis)

	return columns, data, None, chart


def get_formatted_result(args, get_assessment_criteria=False, get_course=False, get_all_assessment_groups=False):
	cond, cond1, cond2, cond3, cond4 = " ", " ", " ", " ", " "
	args_list = [args.academic_year]

	if args.course:
		cond = " and ar.course=%s"
		args_list.append(args.course)

	if args.academic_term:
		cond1 = " and ar.academic_term=%s"
		args_list.append(args.academic_term)

	if args.student_group:
		cond2 = " and ar.student_group=%s"
		args_list.append(args.student_group)

	create_total_dict = False

	assessment_groups = get_child_assessment_groups(args.assessment_group)
	cond3 = " and ar.assessment_group in (%s)"%(', '.join(['%s']*len(assessment_groups)))
	args_list += assessment_groups

	if args.students:
		cond4 = " and ar.student in (%s)"%(', '.join(['%s']*len(args.students)))
		args_list += args.students

	assessment_result = frappe.db.sql('''
		SELECT
			ar.student, ar.student_name, ar.academic_year, ar.academic_term, ar.program, ar.course,
			ar.assessment_plan, ar.grading_scale, ar.assessment_group, ar.student_group,
			ard.assessment_criteria, ard.maximum_score, ard.grade, ard.score
		FROM
			`tabAssessment Result` ar, `tabAssessment Result Detail` ard
		WHERE
			ar.name=ard.parent and ar.docstatus=1 and ar.academic_year=%s {0} {1} {2} {3} {4}
		ORDER BY
			ard.assessment_criteria'''.format(cond, cond1, cond2, cond3, cond4),
		tuple(args_list), as_dict=1)

	# create the nested dictionary structure as given below:
	# <variable_name>.<student_name>.<course>.<assessment_group>.<assessment_criteria>.<grade/score/max_score>
	# "Final Grade" -> assessment criteria used for totaling and args.assessment_group -> for totaling all the assesments

	student_details = {}
	formatted_assessment_result = defaultdict(dict)
	assessment_criteria_dict = OrderedDict()
	course_dict = OrderedDict()
	total_maximum_score = None
	if not (len(assessment_groups) == 1 and assessment_groups[0] == args.assessment_group):
		create_total_dict = True

	# add the score for a given score and recalculate the grades
	def add_score_and_recalculate_grade(result, assessment_group, assessment_criteria):
		formatted_assessment_result[result.student][result.course][assessment_group]\
			[assessment_criteria]["maximum_score"] += result.maximum_score
		formatted_assessment_result[result.student][result.course][assessment_group]\
			[assessment_criteria]["score"] += result.score
		tmp_grade = get_grade(result.grading_scale, ((formatted_assessment_result[result.student][result.course]
			[assessment_group][assessment_criteria]["score"])/(formatted_assessment_result[result.student]
			[result.course][assessment_group][assessment_criteria]["maximum_score"]))*100)
		formatted_assessment_result[result.student][result.course][assessment_group]\
			[assessment_criteria]["grade"] = tmp_grade

	# create the assessment criteria "Final Grade" with the sum of all the scores of the assessment criteria in a given assessment group
	def add_total_score(result, assessment_group):
		if "Final Grade" not in formatted_assessment_result[result.student][result.course][assessment_group]:
			formatted_assessment_result[result.student][result.course][assessment_group]["Final Grade"] = frappe._dict({
				"assessment_criteria": "Final Grade", "maximum_score": result.maximum_score, "score": result.score, "grade": result.grade})
		else:
			add_score_and_recalculate_grade(result, assessment_group, "Final Grade")

	for result in assessment_result:
		if result.student not in student_details:
			student_details[result.student] = result.student_name

		assessment_criteria_details = frappe._dict({"assessment_criteria": result.assessment_criteria,
			"maximum_score": result.maximum_score, "score": result.score, "grade": result.grade})

		if not formatted_assessment_result[result.student]:
			formatted_assessment_result[result.student] = defaultdict(dict)
		if not formatted_assessment_result[result.student][result.course]:
			formatted_assessment_result[result.student][result.course] = defaultdict(dict)

		if not create_total_dict:
			formatted_assessment_result[result.student][result.course][result.assessment_group]\
				[result.assessment_criteria] = assessment_criteria_details
			add_total_score(result, result.assessment_group)

		# create the total of all the assessment groups criteria-wise
		elif create_total_dict:
			if get_all_assessment_groups:
				formatted_assessment_result[result.student][result.course][result.assessment_group]\
					[result.assessment_criteria] = assessment_criteria_details
			if not formatted_assessment_result[result.student][result.course][args.assessment_group]:
				formatted_assessment_result[result.student][result.course][args.assessment_group] = defaultdict(dict)
				formatted_assessment_result[result.student][result.course][args.assessment_group]\
					[result.assessment_criteria] = assessment_criteria_details
			elif result.assessment_criteria not in formatted_assessment_result[result.student][result.course][args.assessment_group]:
				formatted_assessment_result[result.student][result.course][args.assessment_group]\
					[result.assessment_criteria] = assessment_criteria_details
			elif result.assessment_criteria in formatted_assessment_result[result.student][result.course][args.assessment_group]:
				add_score_and_recalculate_grade(result, args.assessment_group, result.assessment_criteria)

			add_total_score(result, args.assessment_group)

		total_maximum_score = formatted_assessment_result[result.student][result.course][args.assessment_group]\
			["Final Grade"]["maximum_score"]
		if get_assessment_criteria:
			assessment_criteria_dict[result.assessment_criteria] = formatted_assessment_result[result.student][result.course]\
				[args.assessment_group][result.assessment_criteria]["maximum_score"]
		if get_course:
			course_dict[result.course] = total_maximum_score

	if get_assessment_criteria and total_maximum_score:
		assessment_criteria_dict["Final Grade"] = total_maximum_score

	return {
		"student_details": student_details,
		"assessment_result": formatted_assessment_result,
		"assessment_criteria": assessment_criteria_dict,
		"course_dict": course_dict
	}


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
			"fieldname": frappe.scrub(d),
			"label": d,
			"fieldtype": "Data",
			"width": 110
		})
		columns.append({
			"fieldname": frappe.scrub(d) +"_score",
			"label": "Score(" + str(int(assessment_criteria[d])) + ")",
			"fieldtype": "Float",
			"width": 100
		})

	return columns


def get_chart_data(grades, criteria_list, kounter):
	grades = sorted(grades)
	datasets = []

	for grade in grades:
		tmp = frappe._dict({"name": grade, "values":[]})
		for criteria in criteria_list:
			if grade in kounter[criteria]:
				tmp["values"].append(kounter[criteria][grade])
			else:
				tmp["values"].append(0)
		datasets.append(tmp)

	return {
		"data": {
			"labels": criteria_list,
			"datasets": datasets
		},
		"type": 'bar',
	}


def get_child_assessment_groups(assessment_group):
	assessment_groups = []
	group_type = frappe.get_value("Assessment Group", assessment_group, "is_group")
	if group_type:
		from frappe.desk.treeview import get_children
		assessment_groups = [d.get("value") for d in get_children("Assessment Group",
			assessment_group) if d.get("value") and not d.get("expandable")]
	else:
		assessment_groups = [assessment_group]
	return assessment_groups
