import frappe


def execute():
	Singles = frappe.qb.DocType("Singles")
	query = (
		frappe.qb.from_(Singles)
		.select("value")
		.where((Singles.doctype == "Accounts Settings") & (Singles.field == "post_change_gl_entries"))
	)
	result = query.run(as_dict=1)
	if result:
		post_change_gl_entries = int(result[0].get("value", 1))
		frappe.db.set_single_value("POS Settings", "post_change_gl_entries", post_change_gl_entries)
