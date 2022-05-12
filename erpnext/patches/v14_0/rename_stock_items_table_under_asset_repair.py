# Copyright (c) 2022, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	if frappe.db.has_column("Asset Repair", "stock_items"):
		rename_field("Asset Repair", "stock_items", "items")

	rename_fields = {"valuation_rate": "rate", "consumed_quantity": "qty", "total_value": "amount"}

	for old, new in rename_fields.items():
		if frappe.db.has_column("Asset Repair Consumed Item", old):
			rename_field("Asset Repair Consumed Item", old, new)
