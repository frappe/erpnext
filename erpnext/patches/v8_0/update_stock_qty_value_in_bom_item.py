# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc('manufacturing', 'doctype', 'bom_item')
	frappe.reload_doc('manufacturing', 'doctype', 'bom_explosion_item')
	frappe.reload_doc('manufacturing', 'doctype', 'bom_scrap_item')
	frappe.db.sql("update `tabBOM Item` set stock_qty = qty, uom = stock_uom, conversion_factor = 1")
	frappe.db.sql("update `tabBOM Explosion Item` set stock_qty = qty")
	if "qty" in frappe.db.get_table_columns("BOM Scrap Item"):
		frappe.db.sql("update `tabBOM Scrap Item` set stock_qty = qty")