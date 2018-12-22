# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

def execute():
	frappe.reload_doctype('Role')
	for dt in ("assessment", "course", "fees"):
		# 'Schools' module changed to the 'Education'
		# frappe.reload_doc("schools", "doctype", dt)
		frappe.reload_doc("education", "doctype", dt)

	for dt in ("domain", "has_domain", "domain_settings"):
		frappe.reload_doc("core", "doctype", dt)

	frappe.reload_doc('website', 'doctype', 'portal_menu_item')

	if 'schools' in frappe.get_installed_apps():
		domain = frappe.get_doc('Domain', 'Education')
		domain.setup_domain()
	else:
		domain = frappe.get_doc('Domain', 'Manufacturing')
		domain.setup_data()
		domain.setup_sidebar_items()
