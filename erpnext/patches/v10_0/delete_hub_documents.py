import frappe


def execute():
	for dt, dn in (("Page", "Hub"), ("DocType", "Hub Settings"), ("DocType", "Hub Category")):
		frappe.delete_doc(dt, dn, ignore_missing=True)

	if frappe.db.exists("DocType", "Data Migration Plan"):
		data_migration_plans = frappe.get_all("Data Migration Plan", filters={"module": "Hub Node"})
		for plan in data_migration_plans:
			plan_doc = frappe.get_doc("Data Migration Plan", plan.name)
			for m in plan_doc.get("mappings"):
				frappe.delete_doc("Data Migration Mapping", m.mapping, force=True)
			docs = frappe.get_all("Data Migration Run", filters={"data_migration_plan": plan.name})
			for doc in docs:
				frappe.delete_doc("Data Migration Run", doc.name)
			frappe.delete_doc("Data Migration Plan", plan.name)
