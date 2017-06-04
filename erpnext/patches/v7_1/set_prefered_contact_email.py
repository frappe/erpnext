from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype('User')
	for d in frappe.get_all("Employee"):
		employee = frappe.get_doc("Employee", d.name)
		if employee.company_email:
			employee.prefered_contact_email = "Company Email"
			employee.prefered_email = employee.company_email
		elif employee.personal_email:
			employee.prefered_contact_email = "Personal Email"
			employee.prefered_email = employee.personal_email
		elif employee.user_id:
			employee.prefered_contact_email = "User ID"
			employee.prefered_email = employee.user_id
		employee.db_update()
