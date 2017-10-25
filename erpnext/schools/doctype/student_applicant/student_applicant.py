# -*- coding: utf-8 -*-777777yyy
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import print_function, unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

class StudentApplicant(Document):
	def autoname(self):
		from frappe.model.naming import set_name_by_naming_series
		if self.student_admission:
			if self.program:
				student_admission = get_student_admission_data(self.student_admission, self.program)
				if student_admission:
					naming_series = student_admission.get("applicant_naming_series")
			else:
				frappe.throw(_("Select the program first"))

			if naming_series:
				self.naming_series = naming_series

		set_name_by_naming_series(self)

	def validate(self):
		self.title = " ".join(filter(None, [self.first_name, self.middle_name, self.last_name]))
		if self.student_admission and self.program and self.date_of_birth:
			self.validation_from_student_admission()

	def on_update_after_submit(self):
		student = frappe.get_list("Student",  filters= {"student_applicant": self.name})
		if student:
			frappe.throw(_("Cannot change status as student {0} is linked with student application {1}").format(student[0].name, self.name))

	def on_submit(self):
		if self.paid and not self.student_admission:
			frappe.throw(_("Please select Student Admission which is mandatory for the paid student applicant"))

	def validation_from_student_admission(self):
		student_admission = get_student_admission_data(self.student_admission, self.program)
		if student_admission:
			if ((
					student_admission.minimum_age
					and getdate(student_admission.minimum_age) > getdate(self.date_of_birth)
				) or (
					student_admission.maximum_age
					and getdate(student_admission.maximum_age) < getdate(self.date_of_birth)
				)):
					frappe.throw(_("Not eligible for the admission in this program as per DOB"))

	def on_payment_authorized(self, *args, **kwargs):
		self.db_set('paid', 1)


def get_student_admission_data(student_admission, program):
	student_admission = frappe.db.sql("""select sa.admission_start_date, sa.admission_end_date,
		sap.program, sap.minimum_age, sap.maximum_age, sap.applicant_naming_series
		from `tabStudent Admission` sa, `tabStudent Admission Program` sap
		where sa.name = sap.parent and sa.name = %s and sap.program = %s""", (student_admission, program), as_dict=1)
	if student_admission:
		return student_admission[0]
	else:
		return None
