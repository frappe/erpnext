import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
    frappe.reload_doc("schools", "doctype", "student_guardian")
    student_guardians = frappe.get_all("Student Guardian", fields=["guardian"])
    for student_guardian in student_guardians:
        guardian_name = frappe.db.get_value("Guardian", student_guardian.guardian, "guardian_name")
        frappe.db.sql("update `tabStudent Guardian` set guardian_name = %s where guardian= %s", (guardian_name, student_guardian.guardian))