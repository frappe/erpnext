import frappe


def execute():
	frappe.reload_doc("manufacturing", "doctype", "work_order")

	for wo in frappe.get_all("Work Order"):
		item_code = frappe.db.get_value("Work Order", wo.name, "production_item")
		item_name = frappe.db.get_value("Item", item_code, "item_name")

		frappe.db.set_value("Work Order", wo.name, "item_name", item_name, update_modified=False)

	frappe.db.commit()