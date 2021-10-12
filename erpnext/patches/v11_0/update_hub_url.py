from __future__ import unicode_literals

import frappe


def execute():
	frappe.reload_doc('hub_node', 'doctype', 'Marketplace Settings')
	frappe.db.set_value('Marketplace Settings', 'Marketplace Settings', 'marketplace_url', 'https://hubmarket.org')
