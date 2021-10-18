# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe


def execute():
	if frappe.db.table_exists('Supplier Item Group'):
		frappe.reload_doc("selling", "doctype", "party_specific_item")
		sig = frappe.db.get_all("Supplier Item Group", fields=["name", "supplier", "item_group"])
		for item in sig:
			psi = frappe.new_doc("Party Specific Item")
			psi.party_type = "Supplier"
			psi.party = item.supplier
			psi.restrict_based_on = "Item Group"
			psi.based_on_value = item.item_group
			psi.insert()
