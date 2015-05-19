# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	frappe.reload_doc("stock", "doctype", "stock_entry")
	if "total_fixed_cost" in frappe.db.get_table_columns("Stock Entry"):
		frappe.db.sql("update `tabStock Entry` set additional_operating_cost = total_fixed_cost")
