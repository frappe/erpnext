import frappe


def execute():
	frappe.reload_doc("vehicles", "doctype", "vehicle_booking_order")

	frappe.db.sql("""
		update `tabVehicle Booking Order`
		set delivery_status = 'Not Received'
		where delivery_status = 'To Receive'
	""")

	frappe.db.sql("""
		update `tabVehicle Booking Order`
		set delivery_status = 'In Stock'
		where delivery_status = 'To Deliver'
	""")

	frappe.db.sql("""
		update `tabVehicle Booking Order`
		set invoice_status = 'Not Received'
		where invoice_status = 'To Receive'
	""")

	frappe.db.sql("""
		update `tabVehicle Booking Order`
		set invoice_status = 'In Hand'
		where invoice_status = 'To Deliver'
	""")
