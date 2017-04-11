import frappe

def execute():
    frappe.reload_doc('schools', 'doctype', 'student_batch_student')
    frappe.reload_doc('schools', 'doctype', 'student_group_student')
    frappe.db.sql("update `tabStudent Batch Student` set active=1")
    frappe.db.sql("update `tabStudent Group Student` set active=1")
