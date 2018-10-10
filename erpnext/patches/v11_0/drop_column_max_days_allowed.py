import frappe

def execute():
	if frappe.db.exists("DocType", "Leave Type"):
		if 'max_days_allowed' in frappe.db.get_table_columns("Leave Type"):
			frappe.db.sql("alter table `tabLeave Type` drop column max_days_allowed")