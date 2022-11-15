# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from erpnext.accounts.doctype.account.account import update_account_number, get_account_autoname

def execute():
	frappe.reload_doc("stock", "doctype", "delivery_note_item")

	names = frappe.get_all("Delivery Note")
	for name in names:
		name = name.name
		doc = frappe.get_doc("Delivery Note", name)
		doc.calculate_alt_uom_tax_inclusive_values()
		for item in doc.items:
			frappe.db.set_value(item.doctype, item.name, {
				"tax_inclusive_amount": item.tax_inclusive_amount,
				"alt_uom_tax_inclusive_rate": item.alt_uom_tax_inclusive_rate
			}, None, update_modified=False)
