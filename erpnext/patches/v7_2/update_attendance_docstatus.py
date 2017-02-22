import frappe

def execute():
	frappe.reload_doctype('Student Attendance')
	# frappe.reload_doc("schools", "doctype", "student_attendance")
	frappe.db.sql('''
		update `tabStudent Attendance` set
			docstatus=0
		where
			docstatus=1''')