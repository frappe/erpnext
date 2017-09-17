import frappe

def execute():
	if frappe.get_meta('Salary Structure').has_field('employee'):
		frappe.db.sql("alter table `tabEmployee` drop column employee")