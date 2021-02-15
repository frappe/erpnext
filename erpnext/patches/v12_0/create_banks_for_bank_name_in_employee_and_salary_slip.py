import frappe


def execute():
	bank_in_employees = frappe.db.sql_list("SELECT DISTINCT bank_name FROM `tabEmployee` WHERE ifnull(bank_name, '') != '' ")
	bank_in_salary_slips = frappe.db.sql_list("SELECT DISTINCT bank_name FROM `tabSalary Slip` WHERE ifnull(bank_name, '') != '' ")

	bank_names = set(bank_in_employees + bank_in_salary_slips)

	for name in bank_names:
		if not frappe.db.exists("Bank", name):
			doc = frappe.new_doc("Bank")
			doc.bank_name = name
			doc.save()
