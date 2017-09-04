from __future__ import unicode_literals
import frappe


def execute():
	if not frappe.db.has_column("Supplier Type", "payment_terms"):
		frappe.db.sql("ALTER TABLE `tabSupplier Type` ADD COLUMN `payment_terms` VARCHAR(140) NULL")
