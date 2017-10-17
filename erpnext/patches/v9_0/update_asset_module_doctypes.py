# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc('assets', 'doctype', 'asset_category')
	frappe.db.set_value("DocType", "Asset Category", "module", "Assets")
	frappe.db.set_value("DocType", "Asset", "module", "Assets")
	frappe.db.set_value("DocType", "Asset Movement", "module", "Assets")
	frappe.db.set_value("DocType", "Depreciation Schedule", "module", "Assets")