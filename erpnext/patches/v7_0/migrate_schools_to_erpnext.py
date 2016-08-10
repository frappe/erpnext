from __future__ import unicode_literals
import frappe

def execute():
	reload_doctypes_for_schools_icons()

	frappe.reload_doc('website', 'doctype', 'portal_settings')
	frappe.reload_doc('website', 'doctype', 'portal_menu_item')
	frappe.reload_doc('buying', 'doctype', 'request_for_quotation')

	if 'schools' in frappe.get_installed_apps():
		frappe.db.sql("""delete from `tabDesktop Icon`""")
		if not frappe.db.exists('Module Def', 'Schools'):
			frappe.get_doc({
				'doctype': 'Module Def',
				'module_name': 'Schools',
				'app_name': 'erpnext'
			}).insert()
		frappe.db.sql("""update `tabDocType` set module='Schools' where module='Academics'""")
		from frappe.installer import remove_from_installed_apps
		remove_from_installed_apps("schools")

def reload_doctypes_for_schools_icons():
	for d in frappe.get_all('DocType', filters={'module': 'Schools'}):
		frappe.reload_doc('schools', 'doctype', d.name)
