# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from collections import defaultdict


def execute(filters=None):
	columns, data = [], []
	student_list_map = defaultdict(list)

	academic_year = filters.get("academic_year")
	program = filters.get("program")
	student_batch_name = filters.get("student_batch_name")

	columns = get_columns(filters)
	
	student_list = frappe.get_list("Program Enrollment", fields=["student", "student_name"],
		filters={"academic_year": academic_year, "program": program, "student_batch_name": student_batch_name})

	student_mobile_map = get_student_mobile_no([d.student for d in student_list])
	guardian_map = get_guardian_map([d.student for d in student_list])
	guardian_mobile_map = get_guardian_mobile_no(set([guardian[2] for student in guardian_map.values() for guardian in student]))

	for student in student_list:
		student_list_map[student.student].append(student.student)
		student_list_map[student.student].append(student.student_name)
		student_list_map[student.student].append(student_mobile_map[student.student])
		student_list_map[student.student].append(guardian_map[student.student][0][0])
		student_list_map[student.student].append(guardian_map[student.student][0][1])
		student_list_map[student.student].append(guardian_mobile_map[guardian_map[student.student][0][2]])
		if len(guardian_map[student.student]) > 1:
			student_list_map[student.student].append(guardian_map[student.student][1][0])
			student_list_map[student.student].append(guardian_map[student.student][1][1])
			student_list_map[student.student].append(guardian_mobile_map[guardian_map[student.student][1][2]])

	data = student_list_map.values()
	return columns, data


def get_columns(filters):
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
	student_mobile_map = {}
	student_mobile_no = frappe.db.sql('''
		select name, student_mobile_number from `tabStudent` where name in (%s)''' %
		', '.join(['%s']*len(student_list)), tuple(student_list), as_dict=1)
	for mobile_no in student_mobile_no:
		student_mobile_map[mobile_no.name] = mobile_no.student_mobile_number
	return student_mobile_map

def get_guardian_map(student_list):
	guardian_map = defaultdict(list)
	guardian_list = frappe.db.sql('''
		select  parent, guardian, guardian_name, relation  from `tabStudent Guardian` where parent in (%s)''' %
		', '.join(['%s']*len(student_list)), tuple(student_list), as_dict=1)
	for guardian in guardian_list:
		guardian_map[guardian.parent].append([guardian.guardian_name, guardian.relation, guardian.guardian])
	return guardian_map

def get_guardian_mobile_no(guardian_list):
	guardian_mobile_map = {}
	guardian_mobile_no = frappe.db.sql('''
		select name, mobile_number from `tabGuardian` where name in (%s)''' %
		', '.join(['%s']*len(guardian_list)), tuple(guardian_list), as_dict=1)
	for mobile_no in guardian_mobile_no:
		guardian_mobile_map[mobile_no.name] = mobile_no.mobile_number
	return guardian_mobile_map
