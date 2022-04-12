import frappe


def execute():
	frappe.db.sql("""
		update `tabVehicle Checklist Item`
		set parentfield = 'vehicle_checklist'
		where parenttype = 'Vehicles Settings' and parentfield = 'vehicle_checklist_items'
	""")
