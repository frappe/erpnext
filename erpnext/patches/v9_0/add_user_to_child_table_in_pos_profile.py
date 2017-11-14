# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	doctype = 'POS Profile'
	frappe.reload_doc('accounts', 'doctype', doctype)
	frappe.reload_doc('accounts', 'doctype', 'POS Profile User')

	for doc in frappe.get_all(doctype):
		_doc = frappe.get_doc(doctype, doc.name)
		user = frappe.db.get_value(doctype, doc.name, 'user')

		if not user: continue

		_doc.append('applicable_for_users', {
			'user': user
		})
		_doc.pos_profile_name = user + ' - ' + _doc.company
		_doc.save()
