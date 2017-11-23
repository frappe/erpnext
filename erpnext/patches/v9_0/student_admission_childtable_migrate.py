# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	# 'Schools' module changed to the 'Education'
	# frappe.reload_doc('schools', 'doctype', 'Student Admission Program')
	# frappe.reload_doc('schools', 'doctype', 'student_admission')
	frappe.reload_doc('education', 'doctype', 'Student Admission Program')
	frappe.reload_doc('education', 'doctype', 'student_admission')

	if "program" not in frappe.db.get_table_columns("Student Admission"):
		return

	student_admissions = frappe.get_all("Student Admission", fields=["name", "application_fee", \
		"naming_series_for_student_applicant", "program", "introduction", "eligibility"])
	for student_admission in student_admissions:
		doc = frappe.get_doc("Student Admission", student_admission.name)
		doc.append("program_details", {
			"program": student_admission.get("program"),
			"application_fee": student_admission.get("application_fee"),
			"applicant_naming_series": student_admission.get("naming_series_for_student_applicant"),
		})
		if student_admission.eligibility and student_admission.introduction:
			doc.introduction = student_admission.introduction + "<br><div>" + \
				student_admission.eligibility + "</div>"
		doc.flags.ignore_validate = True
		doc.flags.ignore_mandatory = True
		doc.save()
