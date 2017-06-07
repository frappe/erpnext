# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	if not filters: filters = {}

	data = []

	results =  get_results(filters)

	columns = get_columns(results)

	for result in results:
		row = [result.course]
		for i in result.assessment_details:
			row.append(i.score)
		row += [result.total_score, result.grade]
		data.append(row)

	return columns, data

def get_results(filters):
	conditions, filters = get_conditions(filters)
	results = frappe.db.sql("""select * from `tabAssessment Result` where docstatus = 1 %s
		order by student_name""" % conditions, filters, as_dict=1)

	if results:
		for res in results:
			res_index = results.index(res)

			if not res.course:
				results[res_index]["course"] = frappe.db.get_value("Assessment Plan",{"name":res.assessment_plan},"course")

			result_details = frappe.db.sql("""select assessment_criteria,score from `tabAssessment Result Detail` where parent = %(parent)s
				""",{"parent":res.name}, as_dict=1)
			if result_details:
				results[res_index].update({"assessment_details": []})
				for det in result_details:
					results[res_index]["assessment_details"].append(det)
		return [x for x in results if "assessment_details" in x]
	else:
		return []


def get_conditions(filters):
	conditions = ""
	if filters.get("student"): conditions += " and student = %(student)s"

	if filters.get("academic_year"): conditions += " and academic_year = %(academic_year)s"
	if filters.get("academic_term"): conditions += " and academic_term = %(academic_term)s"

	return conditions, filters


def get_columns(results):
	if not results:
		return []

	columns = [
		_("Course") + ":Link/Course:220",
	]

	for result in results:
		for a in result["assessment_details"]:
			if not (_(a.assessment_criteria) + "::120") in columns:
				columns.append(_(a.assessment_criteria) + "::120")

	columns += [_("Total") + "::120", _("Grade") + "::120"]

	return columns