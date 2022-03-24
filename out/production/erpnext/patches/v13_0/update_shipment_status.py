import frappe


def execute():
	frappe.reload_doc("stock", "doctype", "shipment")

	# update submitted status
	frappe.db.sql("""UPDATE `tabShipment`
					SET status = "Submitted"
					WHERE status = "Draft" AND docstatus = 1""")

	# update cancelled status
	frappe.db.sql("""UPDATE `tabShipment`
					SET status = "Cancelled"
					WHERE status = "Draft" AND docstatus = 2""")
