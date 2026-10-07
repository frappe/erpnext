import frappe


def execute():
	if not frappe.db.exists("Stock Entry Type", "Batch Split"):
		frappe.new_doc("Stock Entry Type", purpose="Repack", batch_split=1).insert(
			set_name="Batch Split", ignore_permissions=True
		)
