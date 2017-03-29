# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _


def execute(filters=None):
	columns, data = [], []

	academic_year = filters.get("academic_year")
	program = filters.get("program")
	student_batch_name = filters.get("student_batch_name")

	columns = get_columns()
	
	program_enrollments = frappe.get_list("Program Enrollment", fields=["student", "student_name"],
		filters={"academic_year": academic_year, "program": program, "student_batch_name": student_batch_name})

	student_list = [d.student for d in program_enrollments]
	if not student_list:
		return  columns, []

	student_mobile_map = get_student_mobile_no(student_list)
	guardian_map = get_guardian_map(student_list)

	for d in program_enrollments:
		row = [d.student, d.student_name, student_mobile_map.get(d.student)]

		student_guardians = guardian_map.get(d.student)

		if student_guardians:
			for i in xrange(2):
				if i < len(student_guardians):
					g = student_guardians[i]
					row += [g.guardian_name, g.relation, g.mobile_number]

		data.append(row)

	return columns, data


def get_columns():
	columns = [ 
		_("Student ID") + ":Link/Student:90", 
		_("Student Name") + "::150", 
		_("Student Mobile No.") + "::110",
		_("Guardian1 Name") + "::150",
		_("Relation with Guardian1") + "::80",
		_("Guardian1 Mobile No") + "::125",
		_("Guardian2 Name") + "::150",
		_("Relation with Guardian2") + "::80",
		_("Guardian2 Mobile No") + "::125",
	]
	return columns

def get_student_mobile_no(student_list):
	student_mobile_map = frappe._dict()
	student_mobile_no = frappe.db.sql('''
		select name, student_mobile_number from `tabStudent` where name in (%s)''' %
		', '.join(['%s']*len(student_list)), tuple(student_list), as_dict=1)
	for s in student_mobile_no:
		student_mobile_map[s.name] = s.student_mobile_number
	return student_mobile_map

def get_guardian_map(student_list):
	guardian_map = frappe._dict()
	guardian_details = frappe.db.sql('''
		select  parent, guardian, guardian_name, relation  from `tabStudent Guardian` where parent in (%s)''' %
		', '.join(['%s']*len(student_list)), tuple(student_list), as_dict=1)

	guardian_list = list(set([g.guardian for g in guardian_details]))

	guardian_mobile_no = dict(frappe.db.sql("""select name, mobile_number from `tabGuardian` 
			where name in (%s)""" % ", ".join(['%s']*len(guardian_list)), tuple(guardian_list)))

	for guardian in guardian_details:
		guardian["mobile_number"] = guardian_mobile_no.get(guardian.guardian)
		guardian_map.setdefault(guardian.parent, []).append(guardian)

	return guardian_map