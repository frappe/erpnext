# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class ProgramEnrollmentTool(Document):
	def get_students(self):
		if not self.get_students_from:
			frappe.throw(_("Mandatory feild - Get Students From"))
		elif not self.program:
			frappe.throw(_("Mandatory feild - Program"))
		elif not self.academic_year:
			frappe.throw(_("Mandatory feild - Academic Year"))
		else:
			if self.get_students_from == "Student Applicants":
				students = frappe.db.sql("select name as student_applicant, title as student_name from \
					`tabStudent Applicant` where program = %s and academic_year = %s",(self.program, self.academic_year), as_dict=1)
			else:
				students = frappe.db.sql("select student, student_name from \
					`tabProgram Enrollment` where program = %s and academic_year = %s",(self.program, self.academic_year), as_dict=1)
		if students:
			return students
		else:
			frappe.throw(_("No students Found"))
			
	def enroll_students(self):
		for stud in self.students:
			prog_enrollment = frappe.new_doc("Program Enrollment")
			prog_enrollment.student = stud.student
			prog_enrollment.student_name = stud.student_name
			prog_enrollment.program = self.new_program
			prog_enrollment.academic_year = self.new_academic_year
			prog_enrollment.save()
		frappe.msgprint("Students have been enrolled.")
			