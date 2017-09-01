from __future__ import unicode_literals
import frappe


def execute():
	frappe.db.sql("ALTER TABLE `tabGL Entry` ADD COLUMN `due_date` DATE DEFAULT NULL")
