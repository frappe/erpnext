from __future__ import unicode_literals
import frappe

def execute():
	frappe.db.set_value("Features Setup", None, "compact_item_print", 1)
