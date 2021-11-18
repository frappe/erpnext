import frappe

def execute():
	if 'Vehicles' not in frappe.get_active_domains():
		return

	frappe.reload_doc('vehicles', 'doctype', 'vehicle_registration_order')
	frappe.db.sql("""
		update `tabVehicle Registration Order`
		set agent_outstanding = agent_total - agent_payment
	""")
