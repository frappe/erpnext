from __future__ import unicode_literals
import frappe

def execute():
	for role in ('Customer', 'Supplier'):
		frappe.db.sql('''delete from `tabUserRole`
			where role=%s and parent in ("Administrator", "Guest")''', role)

		if not frappe.db.sql('select name from `tabUserRole` where role=%s', role):

			# delete DocPerm
			for doctype in frappe.db.sql('select parent from tabDocPerm where role=%s', role):
				d = frappe.get_doc("DocType", doctype[0])
				d.permissions = [p for p in d.permissions if p.role != role]
				d.save()

			# delete Role
			frappe.delete_doc_if_exists('Role', role)
