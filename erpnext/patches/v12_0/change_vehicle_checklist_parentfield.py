import frappe


def execute():
	if frappe.db.table_exists('tabVehicle Checklist Item'):
		frappe.db.sql("""
			update `tabVehicle Checklist Item`
			set parentfield = 'vehicle_checklist'
			where parenttype = 'Vehicles Settings' and parentfield = 'vehicle_checklist_items'
		""")
