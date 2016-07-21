from __future__ import unicode_literals
import frappe
from erpnext.setup.setup_wizard import domainify

def execute():
	frappe.get_doc('Portal Settings', 'Portal Settings').sync_menu()
	if 'schools' in frappe.get_installed_apps():
		frappe.db.sql("""delete from `tabDesktop Icon`""")
		frappe.db.sql("""update `tabDoctype` set module='Schools' where module='Academics'""")
		from frappe.installer import remove_from_installed_apps
		remove_from_installed_apps("schools")
		domainify.setup_domain('Education')
	else:
		domainify.setup_sidebar_items(domainify.get_domain('Manufacturing'))
