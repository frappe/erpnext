import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	if frappe.db.table_exists("Employee Loan Application") and not frappe.db.table_exists("Loan Application"):
		frappe.rename_doc("DocType", "Employee Loan Application", "Loan Application", force=True)
        frappe.reload_doc("hr", "doctype", "loan_application")

    if frappe.db.table_exists("Employee Loan") and not frappe.db.table_exists("Loan"):
		frappe.rename_doc("DocType", "Employee Loan", "Loan", force=True)
		frappe.reload_doc("hr", "doctype", "loan")

    frappe.reload_doc("hr", "doctype", "salary_slip_loan")
    rename_field("Loan", "employee_loan_account", "loan_account")
    rename_field("Salary Slip Loan", "employee_loan_account", "loan_account")

    for doctype in ['Employee Loan Application', 'Employee Loan']:
			frappe.delete_doc('DocType', doctype)