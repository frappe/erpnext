# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc('manufacturing', 'doctype', 'bom_item')
	frappe.db.sql("update `tabBOM Item` set stock_qty = qty, uom = stock_uom")
	frappe.db.sql("update `tabBOM Explosion Item` set stock_qty = qty")
	frappe.db.sql("update `tabBOM Scrap Item` set stock_qty = qty")