# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	frappe.reload_doctype("Item")
	rename_field("Item", "is_asset_item", "is_fixed_asset")