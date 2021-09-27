import frappe


def execute():
	frappe.db.sql("""
		UPDATE `tabMaintenance Schedule Detail`
		SET completion_status = 'Pending'
		WHERE docstatus < 2
	""")
