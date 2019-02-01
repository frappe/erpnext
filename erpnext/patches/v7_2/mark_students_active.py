from __future__ import unicode_literals
import frappe

def execute():
	# 'Schools' module changed to the 'Education'
	# frappe.reload_doc('schools', 'doctype', 'student_group_student')

	frappe.reload_doc('education', 'doctype', 'student_group_student')
	frappe.db.sql("update `tabStudent Group Student` set active=1")
