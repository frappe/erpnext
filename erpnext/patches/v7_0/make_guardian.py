from __future__ import unicode_literals
import frappe

def execute():
	if frappe.db.exists("DocType", "Student"):
		student_table_cols = frappe.db.get_table_columns("Student")
		if "father_name" in student_table_cols:

			# 'Schools' module changed to the 'Education'
			# frappe.reload_doc("schools", "doctype", "student")
			# frappe.reload_doc("schools", "doctype", "guardian")
			# frappe.reload_doc("schools", "doctype", "guardian_interest")

			frappe.reload_doc("education", "doctype", "student")
			frappe.reload_doc("education", "doctype", "guardian")
			frappe.reload_doc("education", "doctype", "guardian_interest")
			frappe.reload_doc("hr", "doctype", "interest")
		
			fields = ["name", "father_name", "mother_name"]
			
			if "father_email_id" in student_table_cols:
				fields += ["father_email_id", "mother_email_id"]
	
			students = frappe.get_all("Student", fields)
			for stud in students:
				if stud.father_name:
					make_guardian(stud.father_name, stud.name, stud.father_email_id)
				if stud.mother_name:
					make_guardian(stud.mother_name, stud.name, stud.mother_email_id)
		
def make_guardian(name, student, email=None):
	frappe.get_doc({
		'doctype': 'Guardian',
		'guardian_name': name,
		'email': email,
		'student': student
	}).insert()
