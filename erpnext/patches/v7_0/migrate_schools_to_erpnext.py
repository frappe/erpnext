from __future__ import unicode_literals
import frappe, os
from frappe.installer import remove_from_installed_apps

def execute():
	reload_doctypes_for_schools_icons()

	frappe.reload_doc('website', 'doctype', 'portal_settings')
	frappe.reload_doc('website', 'doctype', 'portal_menu_item')
	frappe.reload_doc('buying', 'doctype', 'request_for_quotation')

	if frappe.db.exists("Module Def", "Academics") \
			and frappe.db.get_value("Module Def", "Academics", "app_name") == "schools":
		frappe.db.sql("""delete from `tabDesktop Icon`""")
		
		if not frappe.db.exists('Module Def', 'Schools') and frappe.db.exists('Module Def', 'Academics'):
			frappe.rename_doc("Module Def", "Academics", "Schools")

		remove_from_installed_apps("schools")

def reload_doctypes_for_schools_icons():
	base_path = frappe.get_app_path('erpnext', 'schools', 'doctype')
	for doctype in os.listdir(base_path):
		if os.path.exists(os.path.join(base_path, doctype, doctype + '.json')) \
			and doctype not in ("fee_component", "assessment", "assessment_result"):
			frappe.reload_doc('schools', 'doctype', doctype)