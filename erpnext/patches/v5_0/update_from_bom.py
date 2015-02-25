# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype("BOM")
	frappe.db.sql("update `tabStock Entry` set from_bom = if(ifnull(bom_no, '')='', 0, 1)")
