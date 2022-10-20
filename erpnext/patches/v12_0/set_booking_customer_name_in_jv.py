import frappe


def execute():
	if 'Vehicles' not in frappe.get_active_domains():
		return
	if not frappe.db.has_column("Journal Entry", "vehicle_booking_order"):
		return

	frappe.reload_doctype("Journal Entry")
	frappe.reload_doctype("Journal Entry Account")

	frappe.db.sql("""
		update `tabJournal Entry` jv
		inner join `tabVehicle Booking Order` vbo on vbo.name = jv.vehicle_booking_order
		set jv.booking_customer_name = vbo.customer_name
	""")
	frappe.db.sql("""
		update `tabJournal Entry Account` jva
		inner join `tabVehicle Booking Order` vbo on vbo.name = jva.vehicle_booking_order
		set jva.booking_customer_name = vbo.customer_name
	""")
