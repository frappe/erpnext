from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	if frappe.db.table_exists("Employee Loan Application") and not frappe.db.table_exists("Loan Application"):
		frappe.rename_doc("DocType", "Employee Loan Application", "Loan Application", force=True)

	if frappe.db.table_exists("Employee Loan") and not frappe.db.table_exists("Loan"):
		frappe.rename_doc("DocType", "Employee Loan", "Loan", force=True)

	frappe.reload_doc("hr", "doctype", "loan_application")
	frappe.reload_doc("hr", "doctype", "loan")
	frappe.reload_doc("hr", "doctype", "salary_slip_loan")

	for doctype in ['Loan', 'Salary Slip Loan']:
		if frappe.db.has_column(doctype, 'employee_loan_account'):
			rename_field(doctype, "employee_loan_account", "loan_account")

	columns = {'employee': 'applicant', 'employee_name': 'applicant_name'}
	for doctype in ['Loan Application', 'Loan']:
		frappe.db.sql(""" update `tab{doctype}` set applicant_type = 'Employee' """
			.format(doctype=doctype))
		for column, new_column in columns.items():
			if frappe.db.has_column(doctype, column):
				rename_field(doctype, column, new_column)

		frappe.delete_doc('DocType', doctype)