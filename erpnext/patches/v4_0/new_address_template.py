import frappe

def execute():
	frappe.reload_doc("utilities", "doctype", "address_template")
	d = frappe.new_doc("Address Template")
	d.update({"country":frappe.db.get_default("country")})
	try:
		d.insert()
	except Exception:
		pass
