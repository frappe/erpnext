# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from erpnext.education.utils import validate_duplicate_student
from frappe.utils import cint

class StudentGroup(Document):
	def validate(self):
		self.validate_mandatory_fields()
		self.validate_strength()
		# self.validate_students()
		# self.validate_and_set_child_table_fields()
		# validate_duplicate_student(self.students)

	def validate_mandatory_fields(self):
		if not self.academic_term:
			frappe.throw(_("Please select Academic Term"))
		if self.group_based_on == "Progarm & Stream" and not self.program_and_stream:
			frappe.throw(_("Please select Program And Course Field"))
		if self.group_based_on == "Stream" and not self.stream:
			frappe.throw(_("Please select Stream"))
		if self.group_based_on == "Program" and not self.programs:
			frappe.throw(_("Please select Program"))

	def validate_strength(self):
		if cint(self.max_strength) < 0:
			frappe.throw(_("""Max strength cannot be less than zero."""))
		if self.max_strength and len(self.students) > self.max_strength:
			frappe.throw(_("""Cannot enroll more than {0} students for this student group.""").format(self.max_strength))




@frappe.whitelist()
def get_students(academic_term, group_based_on, program=None, stream=None, program_and_stream=None):
	students_already_alloted_batch = frappe.get_all('Student Group Student',fields=['student','student_phone_number','student_email_id'])
	students_not_given_batch = []
	if group_based_on == 'Program & Stream' and program_and_stream:
		student_list = frappe.db.sql("""
		Select st.title as student,
		st.email_id as student_email_id,
		st.mobile_number as student_phone_number
		FROM 
		`tabEnroll Student` as st
		WHERE 
		st.enrolled_course = %(program_and_stream)s
		AND st.status = 'Active'
		AND st.current_academic_term = %(academic_term)s
		""",{'program_and_stream':program_and_stream,'academic_term':academic_term},as_dict=True)


	# if group_based_on == 'Program' and program :
	# 	student_list = frappe.db.sql("""

	# 	Select st.title as student,
	# 	st.email_id as student_email_id,
	# 	st.mobile_number as student_phone_number
		
	# 	FROM 
	# 	`tabEnroll Student` as st
	# 	JOIN `tabProgram Stream` as psb
	# 	on psb.program_stream_name = st.enrolled_course
	# 	JOIN `tabPograms` as p
	# 	ON p.name = psb.program
	# 	WHERE 
	# 	p.name = %(program)s
	# 	AND st.status = 'Active'
	# 	AND st.current_academic_term = %(academic_term)s
	# 	""",{'program':program,'academic_term':academic_term},as_dict=True)

	# if group_based_on == 'Stream' and stream :
	# 	student_list = frappe.db.sql("""
	# 	Select st.title as student,
	# 	st.email_id as student_email_id,
	# 	st.mobile_number as student_phone_number
		
	# 	FROM 
	# 	`tabEnroll Student` as st
	# 	JOIN `tabProgram Stream` as psb
	# 	on psb.program_stream_name = st.enrolled_course
	# 	JOIN `tabStream` as s
	# 	ON s.name = psb.stream
	# 	WHERE
	# 	s.name = %(stream)s
	# 	AND st.status = 'Active'
	# 	AND st.current_academic_term = %(academic_term)s
	# 	""",{'stream':stream,'academic_term':academic_term},as_dict=True)
	for st in student_list:
		if st not in students_already_alloted_batch:
			students_not_given_batch.append(st)
	if len(students_not_given_batch)==0:
		frappe.throw('No students or all students already alloted a batch')
	return students_not_given_batch


