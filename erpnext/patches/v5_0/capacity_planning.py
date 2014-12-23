# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	frappe.reload_doc("stock", "doctype", "stock_entry")
	frappe.db.sql("update tabBOM set additional_operating_cost = total_fixed_cost")
