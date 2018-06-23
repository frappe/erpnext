import frappe

def execute():
	if 'employee' in frappe.db.get_table_columns("Salary Structure"):
		frappe.db.sql("alter table `tabSalary Structure` drop column employee")
