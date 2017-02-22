# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class StudentAttendanceTool(Document):
	pass

@frappe.whitelist()
def get_student_attendance_records(based_on, date=None, student_batch=None, course_schedule=None):
	student_list = []
	student_attendance_list = []

	if based_on=="Course Schedule":
		student_group = frappe.db.get_value("Course Schedule", course_schedule, "student_group")
		if student_group:
			student_list = frappe.get_list("Student Group Student", fields=["student", "student_name", "idx"] , \
			filters={"parent": student_group, "active": 1}, order_by= "idx")
		else:
			student_batch = frappe.db.get_value("Course Schedule", course_schedule, "student_batch")
	if not student_list: 
		student_list = frappe.get_list("Student Batch Student", fields=["student", "student_name", "idx"] , 
			filters={"parent": student_batch, "active": 1}, order_by= "idx")
	
	if course_schedule:
		student_attendance_list= frappe.db.sql("""select student, status from `tabStudent Attendance` where \
			course_schedule= %s""", (course_schedule), as_dict=1)
	else:
		student_attendance_list= frappe.db.sql("""select student, status from `tabStudent Attendance` where \
			student_batch= %s and date= %s and \
			(course_schedule is Null or course_schedule='')""",
			(student_batch, date), as_dict=1)
	
	for attendance in student_attendance_list:
		for student in student_list:
			if student.student == attendance.student:
				student.status = attendance.status

	return student_list