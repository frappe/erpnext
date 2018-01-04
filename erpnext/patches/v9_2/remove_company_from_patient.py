import frappe

def execute():
	if frappe.db.exists("DocType", "Patient"):
		if 'company' in frappe.db.get_table_columns("Patient"):
			frappe.db.sql("alter table `tabPatient` drop column company")
