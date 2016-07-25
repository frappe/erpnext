# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.model.utils.rename_field import rename_field

def execute():
	if frappe.db.exists("DocType", "Fee Amount"):
		frappe.rename_doc("DocType", "Fee Amount", "Fee Component")
		for dt in ("Fees", "Fee Structure"):
			frappe.reload_doctype(dt)
			rename_field(dt, "amount", "components")
		
	