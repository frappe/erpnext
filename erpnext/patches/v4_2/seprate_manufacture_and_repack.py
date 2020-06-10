# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.db.sql("""update `tabStock Entry` set purpose='Manufacture' where purpose='Manufacture/Repack' and ifnull(work_order,"")!="" """)
	frappe.db.sql("""update `tabStock Entry` set purpose='Repack' where purpose='Manufacture/Repack' and ifnull(work_order,"")="" """)