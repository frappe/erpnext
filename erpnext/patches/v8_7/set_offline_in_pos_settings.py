# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	frappe.reload_doc('accounts', 'doctype', 'pos_settings')

	doc = frappe.get_doc('POS Settings')
	doc.use_pos_in_offline_mode = 1
	doc.save()