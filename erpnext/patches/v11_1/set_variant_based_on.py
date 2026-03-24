# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	item = frappe.qb.DocType("Item")
	frappe.qb.update(item).set(item.variant_based_on, "Item Attribute").where(
		item.variant_based_on.isnull() | (item.variant_based_on == "")
	).where((item.has_variants == 1) | (item.variant_of.isnotnull() & (item.variant_of != ""))).run()
