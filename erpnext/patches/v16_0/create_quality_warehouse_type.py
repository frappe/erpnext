# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

import frappe


def execute():
	"""Seed the 'Quality' Warehouse Type on existing sites.

	New installs get it from install_fixtures. It marks warehouses that hold stock
	quarantined pending quality inspection.
	"""
	if not frappe.db.exists("Warehouse Type", "Quality"):
		frappe.get_doc({"doctype": "Warehouse Type", "name": "Quality"}).insert(ignore_permissions=True)
