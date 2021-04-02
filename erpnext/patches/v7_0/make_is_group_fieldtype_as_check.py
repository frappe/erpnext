from __future__ import unicode_literals
import frappe

def execute():
	for doctype in ["Sales Person", "Customer Group", "Item Group", "Territory"]:
		
		# convert to 1 or 0
		frappe.db.sql("update `tab{doctype}` set is_group = if(is_group='Yes',1,0) "
			.format(doctype=doctype))

		frappe.db.commit()

		# alter fields to int
				
		frappe.db.sql("alter table `tab{doctype}` change is_group is_group int(1) default '0'"
			.format(doctype=doctype))

		frappe.reload_doctype(doctype)
