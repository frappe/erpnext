# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe


def execute():
	frappe.reload_doc("stock", "doctype", "item_manufacturer")

	item_manufacturer = []
	for d in frappe.db.sql(""" SELECT name, manufacturer, manufacturer_part_no, creation, owner
		FROM `tabItem` WHERE manufacturer is not null and manufacturer != ''""", as_dict=1):
		item_manufacturer.append((
			frappe.generate_hash("", 10),
			d.name,
			d.manufacturer,
			d.manufacturer_part_no,
			d.creation,
			d.owner
		))

	if item_manufacturer:
		frappe.db.sql('''
			INSERT INTO `tabItem Manufacturer`
			(`name`, `item_code`, `manufacturer`, `manufacturer_part_no`, `creation`, `owner`)
			VALUES {}'''.format(', '.join(['%s'] * len(item_manufacturer))), tuple(item_manufacturer)
		)
