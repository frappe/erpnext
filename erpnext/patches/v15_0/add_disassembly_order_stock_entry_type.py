import frappe


def execute():
	if not frappe.db.exists("Stock Entry Type", "Disassemble"):
		frappe.get_doc(
			{
				"doctype": "Stock Entry Type",
				"name": "Disassemble",
				"purpose": "Disassemble",
				"is_standard": 1,
			}
		).insert(ignore_permissions=True)
