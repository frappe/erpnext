# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from erpnext.schools.utils import validate_duplicate_student

class StudentGroup(Document):
	def validate(self):
		self.validate_mandatory_fields()
		self.validate_strength()
		if frappe.defaults.get_defaults().student_validation_setting: 
			self.validate_students()
		self.validate_roll_no()
		validate_duplicate_student(self.students)

	def validate_mandatory_fields(self):
		if self.group_based_on == "Course" and not self.course:
			frappe.throw(_("Please select Course"))
		if self.group_based_on == "Course" and (not self.program and self.batch):
			frappe.throw(_("Please select Program"))
		if self.group_based_on == "Batch" and not self.program:
			frappe.throw(_("Please select Program"))

	def validate_strength(self):
		if self.max_strength and len(self.students) > self.max_strength:
			frappe.throw(_("""Cannot enroll more than {0} students for this student group.""").format(self.max_strength))

	def validate_students(self):
		program_enrollment = get_program_enrollment(self.academic_year, self.academic_term, self.program, self.batch, self.course)
		students = [d.student for d in program_enrollment] if program_enrollment else None
		for d in self.students:
			if self.group_based_on != "Activity" and students and d.student not in students and d.active == 1:
				frappe.throw(_("{0} - {1} is not enrolled in the given {2}".format(d.group_roll_number, d.student_name, self.group_based_on)))
			if not frappe.db.get_value("Student", d.student, "enabled") and d.active:
				frappe.throw(_("{0} - {1} is inactive student".format(d.group_roll_number, d.student_name)))

	def validate_roll_no(self):
		roll_no_list = []
		for d in self.students:
			if d.group_roll_number in roll_no_list:
				frappe.throw(_("Duplicate roll number for student {0}".format(d.student_name)))
			else:
				roll_no_list.append(d.group_roll_number)

@frappe.whitelist()
def get_students(academic_year, group_based_on, academic_term=None, program=None, batch=None, course=None):
	enrolled_students = get_program_enrollment(academic_year, academic_term, program, batch, course)

	if enrolled_students:
		student_list = []
		for s in enrolled_students:
			if frappe.db.get_value("Student", s.student, "enabled"):
				s.update({"active": 1})
			else:
				s.update({"active": 0})
			student_list.append(s)
		return student_list
	else:
		frappe.throw(_("No students found"))

def get_program_enrollment(academic_year, academic_term=None, program=None, batch=None, course=None):
	
	condition1 = " "
	condition2 = " "
	if academic_term:
		condition1 += " and pe.academic_term = %(academic_term)s"
	if program:
		condition1 += " and pe.program = %(program)s"
	if batch:
		condition1 += " and pe.student_batch_name = %(batch)s"
	if course:
		condition1 += " and pe.name = pec.parent and pec.course = %(course)s"
		condition2 = ", `tabProgram Enrollment Course` pec"

	return frappe.db.sql('''
		select 
			pe.student, pe.student_name 
		from 
			`tabProgram Enrollment` pe {condition2}
		where
			pe.academic_year = %(academic_year)s  {condition1}
		order by
			pe.student_name asc
		'''.format(condition1=condition1, condition2=condition2),
		({"academic_year": academic_year, "academic_term":academic_term, "program": program, "batch": batch, "course": course}), as_dict=1)

