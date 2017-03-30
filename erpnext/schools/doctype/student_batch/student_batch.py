# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
from erpnext.schools.utils import validate_duplicate_student
import frappe
from frappe import _

class StudentBatch(Document):
	def autoname(self):
		prog_abb = frappe.db.get_value("Program", self.program, "program_abbreviation")
		if not prog_abb:
			prog_abb = self.program
		self.name = prog_abb + "-"+ self.student_batch_name + "-" + self.academic_year
		
	def validate(self):
		validate_duplicate_student(self.students)
		self.validate_name()
		
	def validate_name(self):
		if frappe.db.exists("Student Group", self.name):
			frappe.throw(_("""Student Group exists with same name"""))
