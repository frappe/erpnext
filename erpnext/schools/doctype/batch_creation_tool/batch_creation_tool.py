# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class BatchCreationTool(Document):
	def make_batch(self):
		if self.academic_year and self.program and self.student_batch_name:
			students = frappe.get_list("Program Enrollment", fields=["student", "student_name"],
				 filters={"academic_year":self.academic_year, "program": self.program, "student_batch_name": self.student_batch_name},
				 order_by= "student_name")
			if students:
				student_batch = frappe.new_doc("Student Batch")
				student_batch.update({
					"academic_year": self.academic_year,
					"program": self.program,
					"student_batch_name": self.student_batch_name,
					"students": students
				})
				student_batch.save()
				frappe.msgprint("Student Batch created.")
			else:
				frappe.msgprint("No students found.")
