import frappe


def execute():
	frappe.reload_doc("stock", "doctype", "delivery_note")

	docs = frappe.db.sql("""
		select distinct parenttype, parent
		from `tabHas Role`
		where role = 'Sales User' and parenttype in ('User', 'Role Profile')
	""")

	for dt, name in docs:
		doc = frappe.get_doc(dt, name)
		has_role = [d for d in doc.roles if d.role == "Delivery User"]
		if not has_role:
			row = doc.append("roles")
			row.role = "Delivery User"
			row.db_insert()
