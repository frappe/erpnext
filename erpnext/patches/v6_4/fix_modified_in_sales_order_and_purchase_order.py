from __future__ import unicode_literals
import frappe

def execute():
	for doctype in ("Sales Order", "Purchase Order"):
		data = frappe.db.sql("""select parent, modified_by, modified
			from `tab{doctype} Item` where docstatus=1 group by parent""".format(doctype=doctype), as_dict=True)
		for item in data:
			frappe.db.sql("""update `tab{doctype}` set modified_by=%(modified_by)s, modified=%(modified)s
				where name=%(parent)s""".format(doctype=doctype), item)
