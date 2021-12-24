# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe


def execute():
	'''
		default supplier was not set in the item defaults for multi company instance,
			this patch will set the default supplier

	'''
	if not frappe.db.has_column('Item', 'default_supplier'):
		return

	frappe.reload_doc('stock', 'doctype', 'item_default')
	frappe.reload_doc('stock', 'doctype', 'item')

	companies = frappe.get_all("Company")
	if len(companies) > 1:
		frappe.db.sql(""" UPDATE `tabItem Default`, `tabItem`
			SET `tabItem Default`.default_supplier = `tabItem`.default_supplier
			WHERE
				`tabItem Default`.parent = `tabItem`.name and `tabItem Default`.default_supplier is null
				and `tabItem`.default_supplier is not null and `tabItem`.default_supplier != '' """)
