import frappe


def execute():
	if frappe.db.has_column("Asset Repair", "warehouse"):
		items = frappe.get_all("Asset Repair Consumed Item", fields=["name", "parent"])

		for item in items:
			warehouse = frappe.db.get_value("Asset Repair", item.parent, "warehouse")
			if warehouse:
				frappe.db.set_value("Asset Repair Consumed Item", item.name, "warehouse", warehouse)
		frappe.db.commit()
