# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe


@frappe.whitelist()
def enable_hub():
	hub_settings = frappe.get_doc('Marketplace Settings')
	hub_settings.register()
	frappe.db.commit()
	return hub_settings

@frappe.whitelist()
def sync():
	hub_settings = frappe.get_doc('Marketplace Settings')
	hub_settings.sync()
