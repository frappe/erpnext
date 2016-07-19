from __future__ import unicode_literals
import frappe

def execute():
	frappe.db.sql("""update `tabDoctype` set module='Schools' where module='Academics'""")
	from frappe.installer import remove_from_installed_apps
	remove_from_installed_apps("schools")