# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import random
from datetime import timedelta

import frappe
from frappe.utils import cstr
from frappe.utils.make_random import get_random

from erpnext.education.api import (
	collect_fees,
	enroll_student,
	get_course,
	get_fee_schedule,
	get_student_group_students,
	make_attendance_records,
)


def work():
	frappe.set_user(frappe.db.get_global("demo_education_user"))
	for d in range(20):
		approve_random_student_applicant()
		enroll_random_student(frappe.flags.current_date)
	# if frappe.flags.current_date.weekday()== 0:
	# 	make_course_schedule(frappe.flags.current_date, frappe.utils.add_days(frappe.flags.current_date, 5))
	mark_student_attendance(frappe.flags.current_date)
	# make_assessment_plan()
	make_fees()


def approve_random_student_applicant():
	random_student = get_random("Student Applicant", {"application_status": "Applied"})
	if random_student:
		status = ["Approved", "Rejected"]
		frappe.db.set_value(
			"Student Applicant", random_student, "application_status", status[weighted_choice([9, 3])]
		)


def enroll_random_student(current_date):
	batch = ["Section-A", "Section-B"]
	random_student = get_random("Student Applicant", {"application_status": "Approved"})
	if random_student:
		enrollment = enroll_student(random_student)
		enrollment.academic_year = get_random("Academic Year")
		enrollment.enrollment_date = current_date
		enrollment.student_batch_name = batch[weighted_choice([9, 3])]
		fee_schedule = get_fee_schedule(enrollment.program)
		for fee in fee_schedule:
			enrollment.append("fees", fee)
		enrolled_courses = get_course(enrollment.program)
		for course in enrolled_courses:
			enrollment.append("courses", course)
		enrollment.submit()
		frappe.db.commit()
		assign_student_group(
			enrollment.student,
			enrollment.student_name,
			enrollment.program,
			enrolled_courses,
			enrollment.student_batch_name,
		)


def assign_student_group(student, student_name, program, courses, batch):
	course_list = [d["course"] for d in courses]
	for d in frappe.get_list(
		"Student Group",
		fields=("name"),
		filters={"program": program, "course": ("in", course_list), "disabled": 0},
	):
		student_group = frappe.get_doc("Student Group", d.name)
		student_group.append(
			"students",
			{
				"student": student,
				"student_name": student_name,
				"group_roll_number": len(student_group.students) + 1,
				"active": 1,
			},
		)
		student_group.save()
	student_batch = frappe.get_list(
		"Student Group",
		fields=("name"),
		filters={"program": program, "group_based_on": "Batch", "batch": batch, "disabled": 0},
	)[0]
	student_batch_doc = frappe.get_doc("Student Group", student_batch.name)
	student_batch_doc.append(
		"students",
		{
			"student": student,
			"student_name": student_name,
			"group_roll_number": len(student_batch_doc.students) + 1,
			"active": 1,
		},
	)
	student_batch_doc.save()
	frappe.db.commit()


def mark_student_attendance(current_date):
	status = ["Present", "Absent"]
	for d in frappe.db.get_list("Student Group", filters={"group_based_on": "Batch", "disabled": 0}):
		students = get_student_group_students(d.name)
		for stud in students:
			make_attendance_records(
				stud.student, stud.student_name, status[weighted_choice([9, 4])], None, d.name, current_date
			)


def make_fees():
	for d in range(1, 10):
		random_fee = get_random("Fees", {"paid_amount": 0})
		collect_fees(random_fee, frappe.db.get_value("Fees", random_fee, "outstanding_amount"))


def make_assessment_plan(date):
	for d in range(1, 4):
		random_group = get_random("Student Group", {"group_based_on": "Course", "disabled": 0}, True)
		doc = frappe.new_doc("Assessment Plan")
		doc.student_group = random_group.name
		doc.course = random_group.course
		doc.assessment_group = get_random(
			"Assessment Group", {"is_group": 0, "parent": "2017-18 (Semester 2)"}
		)
		doc.grading_scale = get_random("Grading Scale")
		doc.maximum_assessment_score = 100


def make_course_schedule(start_date, end_date):
	for d in frappe.db.get_list("Student Group"):
		cs = frappe.new_doc("Scheduling Tool")
		cs.student_group = d.name
		cs.room = get_random("Room")
		cs.instructor = get_random("Instructor")
		cs.course_start_date = cstr(start_date)
		cs.course_end_date = cstr(end_date)
		day = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
		for x in range(3):
			random_day = random.choice(day)
			cs.day = random_day
			cs.from_time = timedelta(hours=(random.randrange(7, 17, 1)))
			cs.to_time = cs.from_time + timedelta(hours=1)
			cs.schedule_course()
			day.remove(random_day)


def weighted_choice(weights):
	totals = []
	running_total = 0

	for w in weights:
		running_total += w
		totals.append(running_total)

	rnd = random.random() * running_total
	for i, total in enumerate(totals):
		if rnd < total:
			return i
