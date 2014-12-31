# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("support", "doctype", "maintenance_schedule_detail")
	frappe.reload_doc("support", "doctype", "maintenance_schedule_item")
	
	frappe.db.sql("""update `tabMaintenance Schedule Detail` set sales_person=incharge_name""")
	frappe.db.sql("""update `tabMaintenance Schedule Item` set sales_person=incharge_name""")