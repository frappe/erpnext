# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	if frappe.db.table_exists("POS Profile User"):
		frappe.reload_doc('accounts', 'doctype', 'pos_profile_user')

		frappe.db.sql(""" update `tabPOS Profile User`,
			(select `tabPOS Profile User`.name from `tabPOS Profile User`, `tabPOS Profile`
				where `tabPOS Profile`.name = `tabPOS Profile User`.parent
				group by `tabPOS Profile User`.user, `tabPOS Profile`.company) as pfu
			set
				`tabPOS Profile User`.default = 1
			where `tabPOS Profile User`.name = pfu.name""")
	else:
		doctype = 'POS Profile'
		frappe.reload_doc('accounts', 'doctype', doctype)
		frappe.reload_doc('accounts', 'doctype', 'pos_profile_user')
		frappe.reload_doc('accounts', 'doctype', 'pos_item_group')
		frappe.reload_doc('accounts', 'doctype', 'pos_customer_group')

		for doc in frappe.get_all(doctype):
			_doc = frappe.get_doc(doctype, doc.name)
			user = frappe.db.get_value(doctype, doc.name, 'user')

			if not user: continue

			_doc.append('applicable_for_users', {
				'user': user,
				'default': 1
			})

			_doc.flags.ignore_validate  = True
			_doc.flags.ignore_mandatory = True
			_doc.save()