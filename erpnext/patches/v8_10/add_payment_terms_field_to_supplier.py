from __future__ import unicode_literals
import frappe


def execute():
	if not frappe.db.has_column("Customer", "payment_terms"):
		frappe.db.sql("ALTER TABLE `tabCustomer` ADD COLUMN `payment_terms` DATE DEFAULT NULL")
	if not frappe.db.has_column("Supplier", "payment_terms"):
		frappe.db.sql("ALTER TABLE `tabSupplier` ADD COLUMN `payment_terms` DATE DEFAULT NULL")
