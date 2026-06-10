# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

import frappe


def execute():
	"""Fold the Is Rejected Warehouse checkbox into Warehouse Type.

	Warehouse Type is the single, mutually exclusive classifier (a warehouse
	cannot be both rejected and quality), so rejected warehouses become
	Warehouse Type "Rejected" and the checkbox is removed.
	"""
	if not frappe.db.exists("Warehouse Type", "Rejected"):
		frappe.get_doc({"doctype": "Warehouse Type", "name": "Rejected"}).insert(ignore_permissions=True)

	if frappe.db.has_column("Warehouse", "is_rejected_warehouse"):
		frappe.db.sql(
			"""
			UPDATE `tabWarehouse`
			SET warehouse_type = 'Rejected'
			WHERE is_rejected_warehouse = 1
			"""
		)
