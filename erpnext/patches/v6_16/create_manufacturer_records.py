# Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr

def execute():
	frappe.reload_doc("stock", "doctype", "manufacturer")
	frappe.reload_doctype("Item")
	
	for d in frappe.db.sql("""select distinct manufacturer from tabItem 
		where ifnull(manufacturer, '') != '' and disabled=0"""):
			manufacturer_name = cstr(d[0]).strip()
			if manufacturer_name and not frappe.db.exists("Manufacturer", manufacturer_name):
				man = frappe.new_doc("Manufacturer")
				man.short_name = manufacturer_name
				man.full_name = manufacturer_name
				man.save()
