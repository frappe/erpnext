# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	item_list = frappe.db.sql("""select name from tabItem""", as_dict=1)
	for d in item_list:
		count_stock_entries = frappe.db.sql("""select count(name) from `tabStock Entry Detail` where item_code= %s""",d.get("name"))[0][0]
		
		count_batch_entries = frappe.db.sql("""select count(name) from `tabStock Entry Detail` where \
			item_code= %s and batch_no = '' """,d.get("name"))[0][0]
		
		if count_stock_entries > 0:
			if count_stock_entries == count_batch_entries:
				frappe.db.sql("""update `tabItem` set has_batch_no = 'Yes' where name = %s""",d.get("name"))
				
			if count_batch_entries == 0:
				frappe.db.sql("""update `tabItem` set has_batch_no = 'No' where name = %s""",d.get("name"))
