import frappe
from frappe import _

def execute():
	if not frappe.db.exists("Warehouse", {"warehouse_name": _("Warehouses")}):
		parent_warehouse = frappe.get_doc({
			"doctype": "Warehouse",
			"warehouse_name": _("Warehouses"),
			"is_group": "Yes"
		}).insert(ignore_permissions=True)
		
		for warehouse in frappe.db.sql_list("""select name from tabWarehouse
			where name != %s order by name asc""", "Warehouses - SI"):
			print warehouse
			warehouse = frappe.get_doc("Warehouse", warehouse)
			warehouse.is_group = "No"
			warehouse.parent_warehouse = parent_warehouse.name
			warehouse.save(ignore_permissions=True)