import frappe


def execute():
	if 'Vehicles' not in frappe.get_active_domains():
		return

	frappe.reload_doc("maintenance", "doctype", "maintenance_schedule")
	frappe.reload_doc("maintenance", "doctype", "maintenance_schedule_detail")
	frappe.reload_doc("projects", "doctype", "project_template")

	vehicle_delivery_list = frappe.get_all('Vehicle Delivery', filters={'docstatus': 1}, order_by='posting_date')
	for delivery in vehicle_delivery_list:
		doc = frappe.get_doc('Vehicle Delivery', delivery.name)
		doc.add_vehicle_maintenance_schedule()

	vehicle_gate_pass_list = frappe.get_all('Vehicle Gate Pass', filters={'docstatus': 1}, order_by='posting_date')
	for gate_pass in vehicle_gate_pass_list:
		doc = frappe.get_doc('Vehicle Gate Pass', gate_pass.name)
		doc.add_vehicle_maintenance_schedule()
