# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc('education', 'doctype', 'assessment_plan')

	frappe.db.sql("""
		UPDATE `tabAssessment Plan` as ap
		INNER JOIN `tabStudent Group` as sg ON sg.name = ap.student_group
		SET ap.academic_term = sg.academic_term,
			ap.academic_year = sg.academic_year,
			ap.program = sg.program
		WHERE ap.docstatus = 1
	""")