import frappe


def execute():
	frappe.reload_doc("vehicles", "doctype", "vehicle_registration_order")

	vros = frappe.get_all("Vehicle Registration Order", filters={'status': "To Pay Agent"})
	for d in vros:
		vro = frappe.get_doc("Vehicle Registration Order", d.name)
		vro.set_status(update=True, update_modified=False)
		vro.clear_cache()
