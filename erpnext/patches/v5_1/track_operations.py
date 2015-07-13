from __future__ import unicode_literals

import frappe

def execute():
	frappe.reload_doctype("Production Order")
	frappe.db.sql("""Update `tabProduction Order` as po set track_operations=1 where 
		exists(select name from `tabProduction Order Operation` as po_operation where po_operation.parent = po.name )""")