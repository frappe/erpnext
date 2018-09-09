
import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	for dt, dn in (("Page", "Hub"), ("DocType", "Hub Settings"), ("DocType", "Hub Category")):
		frappe.delete_doc(dt, dn, ignore_missing=True)

	if frappe.db.exists("DocType", "Data Migration Plan"):
		data_migration_plans = frappe.get_all("Data Migration Plan", filters={"module": 'Hub Node'})
		for plan in data_migration_plans:
			plan_doc = frappe.get_doc("Data Migration Plan", plan.name)
			for m in plan_doc.get("mappings"):
				frappe.delete_doc("Data Migration Mapping", m.mapping, force=True)
			frappe.delete_doc("Data Migration Plan", plan.name)

	frappe.delete_doc("Module Def", "Hub Node", ignore_missing=True)
