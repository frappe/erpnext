# Copyright (c) 2022, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	if frappe.db.table_exists("Asset Value Adjustment") and not frappe.db.table_exists(
		"Asset Revaluation"
	):
		frappe.reload_doc("assets", "doctype", "asset_value_adjustment")
		frappe.rename_doc("DocType", "Asset Value Adjustment", "Asset Revaluation", force=True)
		frappe.reload_doc("assets", "doctype", "asset_revaluation")
		frappe.delete_doc_if_exists("DocType", "Asset Value Adjustment")
