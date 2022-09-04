# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from itertools import groupby

import frappe
from frappe import _
from frappe.utils import cint

DOCSTATUS = {
	0: "saved",
	1: "submitted",
}


def execute(filters=None):
	columns, data = [], []

	args = frappe._dict()
	args["assessment_group"] = filters.get("assessment_group")
	args["schedule_date"] = filters.get("schedule_date")

	columns = get_column()

	data, chart = get_assessment_data(args)

	return columns, data, None, chart


def get_assessment_data(args=None):

	# [total, saved, submitted, remaining]
	chart_data = [0, 0, 0, 0]

	condition = ""
	if args["assessment_group"]:
		condition += "and assessment_group = %(assessment_group)s"
	if args["schedule_date"]:
		condition += "and schedule_date <= %(schedule_date)s"

	assessment_plan = frappe.db.sql(
		"""
			SELECT
				ap.name as assessment_plan,
				ap.assessment_name,
				ap.student_group,
				ap.schedule_date,
				(select count(*) from `tabStudent Group Student` sgs where sgs.parent=ap.student_group)
					as student_group_strength
			FROM
				`tabAssessment Plan` ap
			WHERE
				ap.docstatus = 1 {condition}
			ORDER BY
				ap.modified desc
		""".format(
			condition=condition
		),
		(args),
		as_dict=1,
	)

	assessment_plan_list = [d.assessment_plan for d in assessment_plan] if assessment_plan else [""]
	assessment_result = get_assessment_result(assessment_plan_list)

	for d in assessment_plan:

		assessment_plan_details = assessment_result.get(d.assessment_plan)
		assessment_plan_details = (
			frappe._dict() if not assessment_plan_details else frappe._dict(assessment_plan_details)
		)
		if "saved" not in assessment_plan_details:
			assessment_plan_details.update({"saved": 0})
		if "submitted" not in assessment_plan_details:
			assessment_plan_details.update({"submitted": 0})

		# remaining students whose marks not entered
		remaining_students = (
			cint(d.student_group_strength)
			- cint(assessment_plan_details.saved)
			- cint(assessment_plan_details.submitted)
		)
		assessment_plan_details.update({"remaining": remaining_students})
		d.update(assessment_plan_details)

		chart_data[0] += cint(d.student_group_strength)
		chart_data[1] += assessment_plan_details.saved
		chart_data[2] += assessment_plan_details.submitted
		chart_data[3] += assessment_plan_details.remaining

	chart = get_chart(chart_data[1:])

	return assessment_plan, chart


def get_assessment_result(assessment_plan_list):
	assessment_result_dict = frappe._dict()

	assessment_result = frappe.db.sql(
		"""
		SELECT
			assessment_plan, docstatus, count(*) as count
		FROM
			`tabAssessment Result`
		WHERE
			assessment_plan in (%s)
		GROUP BY
			assessment_plan, docstatus
		ORDER BY
			assessment_plan
	"""
		% ", ".join(["%s"] * len(assessment_plan_list)),
		tuple(assessment_plan_list),
		as_dict=1,
	)

	for key, group in groupby(assessment_result, lambda ap: ap["assessment_plan"]):
		tmp = {}
		for d in group:
			if d.docstatus in [0, 1]:
				tmp.update({DOCSTATUS[d.docstatus]: d.count})
		assessment_result_dict[key] = tmp

	return assessment_result_dict


def get_chart(chart_data):
	return {
		"data": {"labels": ["Saved", "Submitted", "Remaining"], "datasets": [{"values": chart_data}]},
		"type": "percentage",
	}


def get_column():
	return [
		{
			"fieldname": "assessment_plan",
			"label": _("Assessment Plan"),
			"fieldtype": "Link",
			"options": "Assessment Plan",
			"width": 120,
		},
		{
			"fieldname": "assessment_name",
			"label": _("Assessment Plan Name"),
			"fieldtype": "Data",
			"options": "",
			"width": 200,
		},
		{
			"fieldname": "schedule_date",
			"label": _("Schedule Date"),
			"fieldtype": "Date",
			"options": "",
			"width": 100,
		},
		{
			"fieldname": "student_group",
			"label": _("Student Group"),
			"fieldtype": "Link",
			"options": "Student Group",
			"width": 200,
		},
		{
			"fieldname": "student_group_strength",
			"label": _("Total Student"),
			"fieldtype": "Data",
			"options": "",
			"width": 100,
		},
		{
			"fieldname": "submitted",
			"label": _("Submitted"),
			"fieldtype": "Data",
			"options": "",
			"width": 100,
		},
		{"fieldname": "saved", "label": _("Saved"), "fieldtype": "Data", "options": "", "width": 100},
		{
			"fieldname": "remaining",
			"label": _("Remaining"),
			"fieldtype": "Data",
			"options": "",
			"width": 100,
		},
	]
