# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Guardian(Document):
	def __setup__(self):
		self.onload()

	def onload(self):
		"""Load Students for quick view"""
		self.load_students()

	def load_students(self):
		"""Load `students` from the database"""
		self.students = []
		students = frappe.get_all("Student Guardian", filters={"guardian":self.name}, fields=["parent"])
		for student in students:
			self.append("students", {
				"student":student.parent,
				"student_name": frappe.db.get_value("Student", student.parent, "title")
			})

	def validate(self):
		self.students = []