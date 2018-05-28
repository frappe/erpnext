import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	frappe.db.sql("""
		UPDATE `tabLeave Type`
		SET max_days_allowed = '0'
		WHERE trim(coalesce(max_days_allowed, '')) = ''
	""")
	frappe.db.sql_ddl("""ALTER table `tabLeave Type` modify max_days_allowed int(8) NOT NULL""")
	frappe.reload_doc("hr", "doctype", "leave_type")
	rename_field("Leave Type", "max_days_allowed", "max_continuous_days_allowed")
