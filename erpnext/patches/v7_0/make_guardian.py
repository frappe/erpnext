from __future__ import unicode_literals
import frappe

def execute():
	if frappe.db.exists("DocType", "Student") and "father_name" in frappe.db.get_table_columns("Student"):
		frappe.reload_doc("schools", "doctype", "student")
		frappe.reload_doc("schools", "doctype", "guardian")
		frappe.reload_doc("schools", "doctype", "guardian_interest")
		frappe.reload_doc("hr", "doctype", "interest")
	
		students = frappe.get_all("Student", fields=["name", "father_name", "father_email_id", 
			"mother_name", "mother_email_id"])
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
