# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from erpnext.setup.setup_wizard.domainify import update_module_def_restrict_to_domain

def execute():
	""" set the restrict to domain in module def """

	frappe.reload_doc("core", "doctype", "module_def")
	if frappe.db.get_single_value('System Settings', 'setup_complete'):
		update_module_def_restrict_to_domain()