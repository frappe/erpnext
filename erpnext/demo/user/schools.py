# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
import random
from frappe.utils import cstr
from frappe.utils.make_random import get_random
from datetime import timedelta
from erpnext.schools.api import get_student_group_students, make_attendance_records, enroll_student, get_fee_schedule, collect_fees

def work():
	frappe.set_user(frappe.db.get_global('demo_schools_user'))
	for d in xrange(20):
		approve_random_student_applicant()
		enroll_random_student(frappe.flags.current_date)
	if frappe.flags.current_date.weekday()== 0:
		make_course_schedule(frappe.flags.current_date, frappe.utils.add_days(frappe.flags.current_date, 5))	
	mark_student_attendance(frappe.flags.current_date)
	make_fees()

def mark_student_attendance(current_date):
	status = ["Present", "Absent"]
	for d in frappe.db.get_list("Course Schedule", filters={"schedule_date": current_date}, fields=("name", "student_group")):
		students = get_student_group_students(d.student_group)
		for stud in students:
			make_attendance_records(stud.student, stud.student_name, d.name, status[weighted_choice([9,4])])
			
def make_fees():
	for d in range(1,10):
		random_fee = get_random("Fees", {"paid_amount": 0})
		collect_fees(random_fee, frappe.db.get_value("Fees", random_fee, "outstanding_amount"))
	
def approve_random_student_applicant():
	random_student = get_random("Student Applicant", {"application_status": "Applied"})
	if random_student:
		status = ["Approved", "Rejected"]
		frappe.db.set_value("Student Applicant", random_student, "application_status", status[weighted_choice([9,3])])

def enroll_random_student(current_date):
	random_student = get_random("Student Applicant", {"application_status": "Approved"})
	if random_student:
		enrollment = enroll_student(random_student)
		enrollment.academic_year = get_random("Academic Year")
		enrollment.enrollment_date = current_date
		fee_schedule = get_fee_schedule(enrollment.program)
		for fee in fee_schedule:
			enrollment.append("fees", fee)
		enrollment.submit()
		frappe.db.commit()
		assign_student_group(enrollment.student, enrollment.program)
		
def assign_student_group(student, program):
	courses = []
	for d in frappe.get_list("Program Course", fields=("course"), filters={"parent": program }):
		courses.append(d.course)

	for d in xrange(3):
		course = random.choice(courses)
		random_sg = get_random("Student Group", {"course": course})
		if random_sg:
			student_group = frappe.get_doc("Student Group", random_sg)
			student_group.append("students", {"student": student})
			student_group.save()
		courses.remove(course)
		
def make_course_schedule(start_date, end_date):
	for d in frappe.db.get_list("Student Group"):
		cs = frappe.new_doc("Scheduling Tool")
		cs.student_group = d.name
		cs.room = get_random("Room")
		cs.instructor = get_random("Instructor")
		cs.course_start_date = cstr(start_date)
		cs.course_end_date = cstr(end_date)
		day = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
		for x in xrange(3):
			random_day = random.choice(day)
			cs.day = random_day
			cs.from_time = timedelta(hours=(random.randrange(7, 17,1)))
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