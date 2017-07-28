# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import money_in_words


class FeeSchedule(Document):
	def validate(self):
		if not(self.programs or self.student_groups):
			frappe.throw(_("Select atleast one {0}").format(self.fee_request_against))
		if self.docstatus:
			self.generate_fee()

	def generate_fee(self):
		if self.fee_request_against == "Program":
			total_fee_count = 0
			for d in self.programs:
				program_enrollment = frappe.get_list("Program Enrollment",
					fields=["name", "student", "student_batch_name", "student_category", "student_name"],
					filters={"program": d.program, "student_batch_name": d.student_batch,
					"academic_year": self.academic_year})
				if program_enrollment:
					d.total_students = len(program_enrollment)
				else:
					d.total_students = 0
				total_fee_count += d.total_students
				for pe in program_enrollment:
					doc = get_mapped_doc("Fee Request", self.name,	{
						"Fee Request": {
							"doctype": "Fees"
						}
					})
					doc.student = pe.student
					doc.student_name = pe.student_name
					doc.program = d.program
					doc.program_enrollment = pe.name
					doc.student_category = pe.student_category
					doc.save()
					doc.submit()
			self.grand_total = total_fee_count*self.total_amount
			self.grand_total_in_words = money_in_words(self.grand_total)


@frappe.whitelist()
def get_fee_structure(source_name,target_doc=None):
	fee_request = get_mapped_doc("Fee Structure", source_name,
		{"Fee Structure": {
			"doctype": "Fee Schedule"
		}}, ignore_permissions=True)
	return fee_request
