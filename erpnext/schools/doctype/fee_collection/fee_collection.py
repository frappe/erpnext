# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext.schools.api import get_student_batch_students, get_student_group_students, get_fee_components

class FeeCollection(Document):
	def on_submit(self):
		students = []
		if self.fee_collection_for == "Student Batch":
			students = get_student_batch_students(self.student_batch)
		elif self.fee_collection_for == "Student Group":
			students = get_student_group_students(self.student_group)
		elif self.fee_collection_for == "Program":
			program_enrollments = frappe.get_all("Program Enrollment", 
				fields=["name", "student", "student_name"],
				filters={"program": self.program, "academic_year": self.academic_year})
		for stud in students:
			self.create_fee_request(stud)

	def create_fee_request(self, stud):
		fee_request = frappe.new_doc("Fee Request")
		fee_components = get_fee_components(self.fee_structure)
		fee_request.update({
			"student": stud.student,
			"student_name": stud.student_name,
			"due_date": self.due_date,
			"student_batch": self.student_batch,
			"student_group": self.student_group,
			"program": self.program,
			"fee_collection": self.name,
			"fee_structure": self.fee_structure,
			"academic_year": self.academic_year,
			"academic_term": self.academic_term,
			"components": fee_components
		})
		if self.fee_collection_for == "Program":
			fee_request.program_enrollment = stud.name
		fee_request.save()
		fee_request.submit()