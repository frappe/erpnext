# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe


def execute():
	frappe.reload_doc('stock', 'doctype', 'landed_cost_voucher')
	frappe.reload_doc('stock', 'doctype', 'landed_cost_item')

	# Calculate and update database
	docnames = frappe.get_all('Landed Cost Voucher')
	for dn in docnames:
		doc = frappe.get_doc('Landed Cost Voucher', dn.name)
		doc.calculate_taxes_and_totals()
		for item in doc.items:
			frappe.db.set_value('Landed Cost Item', item.name, "item_tax_detail", item.item_tax_detail, update_modified=False)

		doc.clear_cache()
