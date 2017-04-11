# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from erpnext.setup.setup_wizard import domainify

def execute():
	frappe.reload_doctype('Role')
	for dt in ("assessment", "course", "fees"):
		frappe.reload_doc("schools", "doctype", dt)

	frappe.reload_doc('website', 'doctype', 'portal_menu_item')

	frappe.get_doc('Portal Settings').sync_menu()

	if 'schools' in frappe.get_installed_apps():
		domainify.setup_domain('Education')
	else:
		domainify.setup_sidebar_items(domainify.get_domain('Manufacturing'))
