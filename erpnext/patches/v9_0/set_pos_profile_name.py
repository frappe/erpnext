# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	doctype = 'POS Profile'
	frappe.reload_doctype(doctype)

	for pos in frappe.get_all(doctype, filters={'disabled': 0}):
		doc = frappe.get_doc(doctype, pos.name)

		if not doc.user or doc.pos_profile_name: continue

		try:
			doc.pos_profile_name = doc.user + ' - ' + doc.company
			doc.flags.ignore_validate  = True
			doc.flags.ignore_mandatory = True
			doc.save()

			frappe.rename_doc(doctype, doc.name, doc.pos_profile_name, force=True)
		except frappe.LinkValidationError:
			frappe.db.set_value("POS Profile", doc.name, 'disabled', 1)
