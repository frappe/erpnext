import frappe

def execute():
	frappe.reload_doc("education", "doctype", "student_attendance")
	frappe.db.sql('''
		update `tabStudent Attendance` set
			docstatus=0
		where
			docstatus=1''')