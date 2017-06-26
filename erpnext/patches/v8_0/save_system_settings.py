# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	"""
		save system settings document
	"""

	frappe.reload_doc("core", "doctype", "system_settings")
	doc = frappe.get_doc("System Settings", "System Settings")
	doc.flags.ignore_mandatory = True
	doc.save(ignore_permissions=True)
