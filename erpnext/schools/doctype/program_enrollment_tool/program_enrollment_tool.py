# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.schools.api import enroll_student

class ProgramEnrollmentTool(Document):
	def get_students(self):
		if not self.get_students_from:
			frappe.throw(_("Mandatory field - Get Students From"))
		elif not self.program:
			frappe.throw(_("Mandatory field - Program"))
		elif not self.academic_year:
			frappe.throw(_("Mandatory field - Academic Year"))
		else:
			if self.get_students_from == "Student Applicants":
				students = frappe.db.sql("select name as student_applicant, title as student_name from \
					`tabStudent Applicant` where program = %s and academic_year = %s",(self.program, self.academic_year), as_dict=1)
			else:
				students = frappe.db.sql("select student, student_name, student_batch_name from \
					`tabProgram Enrollment` where program = %s and academic_year = %s",(self.program, self.academic_year), as_dict=1)
				student_list = [d.student for d in students]

				inactive_students = frappe.db.sql('''
					select name as student, title as student_name from `tabStudent` where name in (%s) and enabled = 0''' %
					', '.join(['%s']*len(student_list)), tuple(student_list), as_dict=1)

				for student in students:
					if student.student in [d.student for d in inactive_students]:
						students.remove(student)

		if students:
			return students
		else:
			frappe.throw(_("No students Found"))
			
	def enroll_students(self):
		for stud in self.students:
			if stud.student:
				prog_enrollment = frappe.new_doc("Program Enrollment")
				prog_enrollment.student = stud.student
				prog_enrollment.student_name = stud.student_name
				prog_enrollment.student_batch_name = stud.student_batch_name
				prog_enrollment.program = self.new_program
				prog_enrollment.academic_year = self.new_academic_year
				prog_enrollment.save()
			elif stud.student_applicant:
				prog_enrollment = enroll_student(stud.student_applicant)
				prog_enrollment.academic_year = self.academic_year
				prog_enrollment.save()
		frappe.msgprint("Students have been enrolled.")
			