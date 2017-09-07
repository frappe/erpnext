# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc('accounts', 'doctype', 'pos_settings')

	doc = frappe.get_doc('POS Settings')
	doc.is_online = 0
	doc.save()