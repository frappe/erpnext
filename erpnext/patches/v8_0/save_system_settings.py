# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint

def execute():
	"""
		save system settings document
	"""

	frappe.reload_doc("core", "doctype", "system_settings")
	doc = frappe.get_doc("System Settings")
	doc.flags.ignore_mandatory = True

	if cint(doc.currency_precision) == 0:
		doc.currency_precision = ''

	doc.save(ignore_permissions=True)
