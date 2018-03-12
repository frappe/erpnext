import frappe

def create_shipper(service_name):
	if not frappe.db.exists("Shipper", service_name):
		frappe.get_doc({
			"doctype": "Shipper",
			"shipper": service_name
		}).insert(ignore_permissions=True) 