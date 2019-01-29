from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("stock", "doctype", "warehouse")
	frappe.db.sql("""update tabWarehouse
		set is_group = if ((ifnull(is_group, "No") = "Yes" or ifnull(is_group, 0) = 1), 1, 0)""")