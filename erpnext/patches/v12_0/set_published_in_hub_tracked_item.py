import frappe


def execute():
	frappe.reload_doc("Hub Node", "doctype", "Hub Tracked Item")
	if not frappe.db.a_row_exists("Hub Tracked Item"):
		return

	frappe.db.sql(
		"""
		Update `tabHub Tracked Item`
		SET published = 1
	"""
	)
