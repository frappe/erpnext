import frappe


def execute():
	homepage = frappe.get_doc("Homepage")

	for row in homepage.products:
		web_item = frappe.db.get_value("Website Item", {"item_code": row.item_code}, "name")
		if not web_item:
			continue

		row.item_code = web_item

	homepage.flags.ignore_mandatory = True
	homepage.save()
