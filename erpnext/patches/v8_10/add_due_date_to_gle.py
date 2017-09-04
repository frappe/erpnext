from __future__ import unicode_literals
import frappe


def execute():
	if not frappe.db.has_column("GL Entry", "due_date"):
		frappe.db.sql("ALTER TABLE `tabGL Entry` ADD COLUMN `due_date` DATE DEFAULT NULL")
