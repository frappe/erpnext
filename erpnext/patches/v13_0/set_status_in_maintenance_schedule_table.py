import frappe


def execute():
	frappe.reload_doc("maintenance", "doctype", "Maintenance Schedule Detail")
	frappe.db.sql(
		"""
		UPDATE `tabMaintenance Schedule Detail`
		SET completion_status = 'Pending'
		WHERE docstatus < 2
	"""
	)
