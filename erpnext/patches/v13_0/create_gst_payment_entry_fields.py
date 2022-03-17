# Copyright (c) 2021, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe


# Patch kept for users outside India
def execute():
	if frappe.db.exists("Company", {"country": "India"}):
		return

	for field in (
		"gst_section",
		"company_address",
		"company_gstin",
		"place_of_supply",
		"customer_address",
		"customer_gstin",
	):
		frappe.delete_doc_if_exists("Custom Field", f"Payment Entry-{field}")
