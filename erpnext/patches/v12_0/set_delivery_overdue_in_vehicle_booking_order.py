import frappe


def execute():
	frappe.reload_doc("vehicles", "doctype", "vehicle_booking_order")

	to_update = frappe.get_all("Vehicle Booking Order",
		{'status': ['in', ['To Assign Vehicle', 'Delivery Overdue']]})

	for d in to_update:
		doc = frappe.get_doc("Vehicle Booking Order", d.name)
		if doc.status == "Delivery Overdue":
			doc.db_set('delivery_overdue', 1, update_modified=False)

		doc.set_status(update=True, update_modified=False)
