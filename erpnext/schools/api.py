# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, cstr
from frappe.email.doctype.email_group.email_group import add_subscribers

def get_course(program):
	'''Return list of courses for a particular program
	:param program: Program
	'''
	courses = frappe.db.sql('''select course, course_name from `tabProgram Course` where parent=%s''',
			(program), as_dict=1)
	return courses

@frappe.whitelist()
def enroll_student(source_name):
	"""Creates a Student Record and returns a Program Enrollment.

	:param source_name: Student Applicant.
	"""
	frappe.publish_realtime('enroll_student_progress', {"progress": [1, 4]}, user=frappe.session.user)
	student = get_mapped_doc("Student Applicant", source_name,
		{"Student Applicant": {
			"doctype": "Student",
			"field_map": {
				"name": "student_applicant"
			}
		}}, ignore_permissions=True)
	student.save()
	program_enrollment = frappe.new_doc("Program Enrollment")
	program_enrollment.student = student.name
	program_enrollment.student_name = student.title
	program_enrollment.program = frappe.db.get_value("Student Applicant", source_name, "program")
	frappe.publish_realtime('enroll_student_progress', {"progress": [4, 4]}, user=frappe.session.user)	
	return program_enrollment

@frappe.whitelist()
def check_attendance_records_exist(course_schedule=None, student_group=None, date=None):
	"""Check if Attendance Records are made against the specified Course Schedule or Student Group for given date.

	:param course_schedule: Course Schedule.
	:param student_group: Student Group.
	:param date: Date.
	"""
	if course_schedule:
		return frappe.get_list("Student Attendance", filters={"course_schedule": course_schedule})
	else:
		return frappe.get_list("Student Attendance", filters={"student_group": student_group, "date": date})

@frappe.whitelist()
def mark_attendance(students_present, students_absent, course_schedule=None, student_group=None, date=None):
	"""Creates Multiple Attendance Records.

	:param students_present: Students Present JSON.
	:param students_absent: Students Absent JSON.
	:param course_schedule: Course Schedule.
	:param student_group: Student Group.
	:param date: Date.
	"""
	 
	present = json.loads(students_present)
	absent = json.loads(students_absent)
	
	for d in present:
		make_attendance_records(d["student"], d["student_name"], "Present", course_schedule, student_group, date)

	for d in absent:
		make_attendance_records(d["student"], d["student_name"], "Absent", course_schedule, student_group, date)

	frappe.db.commit()
	frappe.msgprint(_("Attendance has been marked successfully."))

def make_attendance_records(student, student_name, status, course_schedule=None, student_group=None, date=None):
	"""Creates/Update Attendance Record.

	:param student: Student.
	:param student_name: Student Name.
	:param course_schedule: Course Schedule.
	:param status: Status (Present/Absent)
	"""
	student_attendance_list = frappe.get_list("Student Attendance", fields = ['name'], filters = {
		"student": student,
		"course_schedule": course_schedule,
		"student_group": student_group,
		"date": date
	})
		
	if student_attendance_list:
		student_attendance = frappe.get_doc("Student Attendance", student_attendance_list[0])
	else:
		student_attendance = frappe.new_doc("Student Attendance")
	student_attendance.student = student
	student_attendance.student_name = student_name
	student_attendance.course_schedule = course_schedule
	student_attendance.student_group = student_group
	student_attendance.date = date
	student_attendance.status = status
	student_attendance.save()

@frappe.whitelist()
def get_student_guardians(student):
	"""Returns List of Guardians of a Student.

	:param student: Student.
	"""
	guardians = frappe.get_list("Student Guardian", fields=["guardian"] , 
		filters={"parent": student})
	return guardians

@frappe.whitelist()
def get_student_group_students(student_group, include_inactive=0):
	"""Returns List of student, student_name in Student Group.

	:param student_group: Student Group.
	"""
	if include_inactive:
		students = frappe.get_list("Student Group Student", fields=["student", "student_name"] ,
			filters={"parent": student_group}, order_by= "group_roll_number")
	else:
		students = frappe.get_list("Student Group Student", fields=["student", "student_name"] ,
			filters={"parent": student_group, "active": 1}, order_by= "group_roll_number")
	return students

@frappe.whitelist()
def get_fee_structure(program, academic_term=None):
	"""Returns Fee Structure.

	:param program: Program.
	:param academic_term: Academic Term.
	"""
	fee_structure = frappe.db.get_values("Fee Structure", {"program": program,
		"academic_term": academic_term}, 'name', as_dict=True)
	return fee_structure[0].name if fee_structure else None

@frappe.whitelist()
def get_fee_components(fee_structure):
	"""Returns Fee Components.

	:param fee_structure: Fee Structure.
	"""
	if fee_structure:
		fs = frappe.get_list("Fee Component", fields=["fees_category", "amount"] , filters={"parent": fee_structure}, order_by= "idx")
		return fs

@frappe.whitelist()
def get_fee_schedule(program, student_category=None):
	"""Returns Fee Schedule.

	:param program: Program.
	:param student_category: Student Category
	"""
	fs = frappe.get_list("Program Fee", fields=["academic_term", "fee_structure", "due_date", "amount"] ,
		filters={"parent": program, "student_category": student_category }, order_by= "idx")
	return fs

@frappe.whitelist()
def collect_fees(fees, amt):
	paid_amount = flt(amt) + flt(frappe.db.get_value("Fees", fees, "paid_amount"))
	total_amount = flt(frappe.db.get_value("Fees", fees, "total_amount"))
	frappe.db.set_value("Fees", fees, "paid_amount", paid_amount)
	frappe.db.set_value("Fees", fees, "outstanding_amount", (total_amount - paid_amount))
	return paid_amount

@frappe.whitelist()
def get_course_schedule_events(start, end, filters=None):
	"""Returns events for Course Schedule Calendar view rendering.

	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters (JSON).
	"""
	from frappe.desk.calendar import get_event_conditions
	conditions = get_event_conditions("Course Schedule", filters)

	data = frappe.db.sql("""select name, course,
			timestamp(schedule_date, from_time) as from_datetime,
			timestamp(schedule_date, to_time) as to_datetime,
			room, student_group, 0 as 'allDay'
		from `tabCourse Schedule`
		where ( schedule_date between %(start)s and %(end)s )
		{conditions}""".format(conditions=conditions), {
			"start": start,
			"end": end
			}, as_dict=True, update={"allDay": 0})

	return data

@frappe.whitelist()
def get_assessment_criteria(course):
	"""Returns Assessmemt Criteria and their Weightage from Course Master.

	:param Course: Course
	"""
	return frappe.get_list("Course Assessment Criteria", \
		fields=["assessment_criteria", "weightage"], filters={"parent": course}, order_by= "idx")

@frappe.whitelist()
def get_assessment_students(assessment_plan, student_group):
	
	student_list = get_student_group_students(student_group)
	for i, student in enumerate(student_list):
		result = get_result(student.student, assessment_plan)
		if result:
			student_result = {}
			for d in result.details:
				student_result.update({d.assessment_criteria: cstr(d.score) + " ("+ d.grade + ")"})
			student_result.update({"total_score": cstr(result.total_score) + " (" + result.grade + ")"})
			student.update({'assessment_details': student_result})
		else:
			student.update({'assessment_details': None})
	return student_list

@frappe.whitelist()
def get_assessment_details(assessment_plan):
	"""Returns Assessment Criteria  and Maximum Score from Assessment Plan Master.

	:param Assessment Plan: Assessment Plan
	"""
	return frappe.get_list("Assessment Plan Criteria", \
		fields=["assessment_criteria", "maximum_score"], filters={"parent": assessment_plan}, order_by= "idx")

@frappe.whitelist()
def get_result(student, assessment_plan):
	"""Returns Submitted Result of given student for specified Assessment Plan

	:param Student: Student
	:param Assessment Plan: Assessment Plan
	"""
	results = frappe.get_all("Assessment Result", filters={"student": student, "assessment_plan": assessment_plan, "docstatus": 1})
	if results:
		return frappe.get_doc("Assessment Result", results[0])
	else:
		return None

@frappe.whitelist()
def get_grade(grading_scale, percentage):
	"""Returns Grade based on the Grading Scale and Score.

	:param Grading Scale: Grading Scale
	:param Percentage: Score Percentage Percentage
	"""
	grading_scale_intervals = {}
	for d in frappe.get_all("Grading Scale Interval", fields=["grade_code", "threshold"], filters={"parent": grading_scale}):
		grading_scale_intervals.update({d.threshold:d.grade_code})
	intervals = sorted(grading_scale_intervals.keys(), key=float, reverse=True)
	for interval in intervals:
		if flt(percentage) >= interval:
			grade = grading_scale_intervals.get(interval)
			break
		else:
			grade = ""
	return grade

@frappe.whitelist()
def mark_assessment_result(student, assessment_plan, scores):
	student_score = json.loads(scores)
	details = []
	for s in student_score.keys():
		details.append({
			"assessment_criteria": s,
			"score": flt(student_score[s])
		})
	assessment_result = frappe.new_doc("Assessment Result")
	assessment_result.update({
		"student": student,
		"student_name": frappe.db.get_value("Student", student, "title"),
		"assessment_plan": assessment_plan,
		"details": details
	})
	assessment_result.save()
	assessment_result.submit()	
	return assessment_result

@frappe.whitelist()
def update_email_group(doctype, name):
	if not frappe.db.exists("Email Group", name):
		email_group = frappe.new_doc("Email Group")
		email_group.title = name
		email_group.save()
	email_list = []
	students = []
	if doctype == "Student Group":
		students = get_student_group_students(name)
	for stud in students:
		for guard in get_student_guardians(stud.student):
			email = frappe.db.get_value("Guardian", guard.guardian, "email_address")
			if email:
				email_list.append(email)	
	add_subscribers(name, email_list)
