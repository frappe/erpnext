# Copyright (c) 2022, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	if not frappe.db.count("Item"):
		return

	if frappe.db.has_column("Item", "is_grouped_asset"):
		frappe.reload_doctype("Item")

		frappe.db.sql(
			"""
			UPDATE
				`tabItem`
			SET
				is_serialized_asset = 0
			WHERE
				is_fixed_asset = 1
				and auto_create_assets = 1
			"""
		)
