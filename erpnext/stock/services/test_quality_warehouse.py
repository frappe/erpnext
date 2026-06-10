# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

"""Shared warehouse helpers for the quality test suites."""

import frappe


def ensure_quality_warehouse_type():
	if not frappe.db.exists("Warehouse Type", "Quality"):
		frappe.get_doc({"doctype": "Warehouse Type", "name": "Quality"}).insert(ignore_permissions=True)


def make_warehouse(name, warehouse_type=None, quality_warehouse=None):
	full = f"{name} - _TC"
	if not frappe.db.exists("Warehouse", full):
		frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": name,
				"company": "_Test Company",
				"warehouse_type": warehouse_type,
				"quality_warehouse": quality_warehouse,
			}
		).insert(ignore_permissions=True)
	return full
