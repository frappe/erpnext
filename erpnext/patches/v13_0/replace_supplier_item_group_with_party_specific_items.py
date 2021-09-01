# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

def execute():
	sig = frappe.db.get_all("Supplier Item Group", fields=["name", "supplier", "item_group"])
	for item in sig:
		psi = frappe.new_doc("Party Specific Items")
		psi.party_type = "Supplier"
		psi.party = item.supplier
		psi.restrict_based_on = "Item Group"
		psi.based_on = item.item_group
		psi.insert()

	supplier_dt = frappe.get_doc("DocType", "Supplier")
	for link in supplier_dt.links:
		if link.link_doctype == "Supplier Item Group":
			supplier_dt.links.remove(link)
			supplier_dt.append('links', {'link_doctype': 'Party Specific Items', 'link_fieldname':'party'})
			supplier_dt.save()
	frappe.delete_doc("DocType", "Supplier Item Group", force=1)
