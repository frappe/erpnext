import frappe
from frappe import _

def execute():
	for warehouse in frappe.db.sql_list("""select name from tabWarehouse
		order by company asc, name asc"""):
		warehouse = frappe.get_doc("Warehouse", warehouse)
		warehouse.is_group = "No"
		warehouse.parent_warehouse = ""
		warehouse.save(ignore_permissions=True)