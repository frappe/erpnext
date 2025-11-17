import frappe


def execute():
	warehouses = frappe.get_single_value(
		"Manufacturing Settings",
		["default_wip_warehouse", "default_fg_warehouse", "default_scrap_warehouse"],
		as_dict=True,
	)

	for name, warehouse in warehouses.items():
		if warehouse:
			company = frappe.get_value("Warehouse", warehouse, "company")
			frappe.db.set_value("Company", company, name, warehouse)
