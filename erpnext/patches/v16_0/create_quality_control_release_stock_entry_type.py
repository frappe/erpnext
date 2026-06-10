# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

import frappe


def execute():
	"""Seed the standard 'Quality Control Release' Stock Entry Type on existing sites.

	New installs get it from install_fixtures; this backfills it so the QC
	Release purpose (used to release quarantined stock out of a Quality
	warehouse) resolves to a standard Stock Entry Type.
	"""
	if frappe.db.exists("Stock Entry Type", "Quality Control Release"):
		return

	frappe.get_doc(
		{
			"doctype": "Stock Entry Type",
			"name": "Quality Control Release",
			"purpose": "Quality Control Release",
			"is_standard": 1,
		}
	).insert(ignore_permissions=True)
