# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	frappe.reload_doc("stock", "doctype", "pick_list")
	frappe.db.set_value(
		"Pick List",
		{"docstatus": 1, "purpose": "Delivery against Sales Order"},
		"purpose",
		"Delivery",
		update_modified=False,
	)
