# Copyright (c) 2022, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	if not frappe.db.count("Asset"):
		return

	doctypes = ["Asset Repair", "Asset Maintenance", "Asset Revaluation", "Asset Movement Item"]

	for doctype in doctypes:
		if frappe.db.count(doctype):
			frappe.reload_doctype(doctype)

			frappe.db.sql(
				"""
				UPDATE
					`tab%s`
				SET
					num_of_assets = 1
				""",
				doctype,
			)
