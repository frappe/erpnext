# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	doctype = 'POS Profile'
	frappe.reload_doctype(doctype)

	for pos in frappe.get_all(doctype):
		doc = frappe.get_doc(doctype, pos.name)

		if not doc.user: continue

		doc.pos_profile_name = doc.user + ' - ' + doc.company
		doc.save()

		frappe.rename_doc(doctype, doc.name, doc.pos_profile_name, force=True)