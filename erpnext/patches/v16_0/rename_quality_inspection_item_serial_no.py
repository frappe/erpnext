# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doc("stock", "doctype", "quality_inspection")
	if frappe.db.has_column("Quality Inspection", "item_serial_no"):
		rename_field("Quality Inspection", "item_serial_no", "serial_no")
