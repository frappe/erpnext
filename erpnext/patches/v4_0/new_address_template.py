import frappe

def execute():
	d = frappe.new_doc("Address Template")
	d.update({"country":frappe.db.get_default("country")})
	try:
		d.insert()
	except Exception:
		pass
