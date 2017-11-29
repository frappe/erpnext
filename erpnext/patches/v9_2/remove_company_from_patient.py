import frappe

def execute():
	if 'company' in frappe.db.get_table_columns("Patient"):
		frappe.db.sql("alter table `tabPatient` drop column company")
