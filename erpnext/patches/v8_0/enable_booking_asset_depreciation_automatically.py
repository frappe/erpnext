# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.db.set_value("Accounts Settings", None, 
		"book_asset_depreciation_entry_automatically", 1)