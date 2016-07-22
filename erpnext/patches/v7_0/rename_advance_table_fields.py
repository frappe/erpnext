# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	for dt in ("Sales Invoice Advance", "Purchase Invoice Advance"):
		frappe.reload_doctype(dt)
		
		frappe.db.sql("update `tab{0}` set reference_type = 'Journal Entry'".format(dt))
		
		rename_field(dt, "journal_entry", "reference_name")
		rename_field(dt, "jv_detail_no", "reference_row")