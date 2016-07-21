from __future__ import unicode_literals
import frappe
from erpnext.setup.setup_wizard import domainify

def execute():
	if 'schools' in frappe.get_installed_apps():
		frappe.get_doc('Portal Settings', 'Portal Settings').sync_menu()
		frappe.db.sql("""delete from `tabDesktop Icon`""")
		frappe.db.sql("""update `tabDocType` set module='Schools' where module='Academics'""")
		from frappe.installer import remove_from_installed_apps
		remove_from_installed_apps("schools")
		domainify.setup_domain('Education')
	else:
		frappe.reload_doctype('Announcement')
		frappe.reload_doctype('Course')
		frappe.reload_doctype('Fees')
		frappe.reload_doctype('Examination')
		frappe.get_doc('Portal Settings', 'Portal Settings').sync_menu()
		domainify.setup_sidebar_items(domainify.get_domain('Manufacturing'))
