# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe


def execute():
	frappe.reload_doc("stock", "doctype", frappe.scrub("Stock Settings"))
	frappe.db.set_single_value("Stock Settings", "allow_existing_serial_no", 1, update_modified=False)
