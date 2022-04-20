import frappe


def execute():
	if 'Vehicles' not in frappe.get_active_domains():
		return

	if frappe.db.has_column('Project', 'vehicle_received_dt'):
		frappe.db.sql("""
			update `tabProject`
			set vehicle_received_date = date(vehicle_received_dt), vehicle_received_time = time(vehicle_received_dt)
			where ifnull(vehicle_received_dt, '') != ''
		""")

	if frappe.db.has_column('Project', 'vehicle_delivered_dt'):
		frappe.db.sql("""
			update `tabProject`
			set vehicle_delivered_date = date(vehicle_delivered_dt), vehicle_delivered_time = time(vehicle_delivered_dt)
			where ifnull(vehicle_delivered_dt, '') != ''
		""")

	frappe.delete_doc_if_exists("Custom Field", "Project-vehicle_received_dt")
	frappe.delete_doc_if_exists("Custom Field", "Project-vehicle_delivered_dt")
