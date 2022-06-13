# Copyright (c) 2022, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doc("assets", "doctype", "asset_maintenance")

	if frappe.db.has_column("Asset Maintenance", "asset_name"):
		rename_field("Asset Maintenance", "asset_name", "asset")
