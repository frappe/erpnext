import frappe
import frappe.defaults

FIELDS = ("default_warehouse", "sample_retention_warehouse")


def execute():
	"""Move the global warehouse defaults from Stock Settings onto the Company that owns them."""
	settings = frappe.db.get_singles_dict("Stock Settings")
	warehouses = {field: settings.get(field) for field in FIELDS if settings.get(field)}
	if not warehouses:
		return

	for field, warehouse in warehouses.items():
		company = frappe.db.get_value("Warehouse", warehouse, "company")
		if company:
			frappe.db.set_value("Company", company, field, warehouse)

	frappe.db.delete("Singles", {"doctype": "Stock Settings", "field": ("in", FIELDS)})
	frappe.defaults.clear_default("default_warehouse")
