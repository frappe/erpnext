import frappe


def execute():
	frappe.reload_doc("vehicles", "doctype", "vehicle_transfer_letter")
	frappe.db.sql("""
		update `tabVehicle Transfer Letter` vtl
		inner join `tabCustomer` c on c.name = vtl.customer
		set vtl.territory = c.territory
	""")
