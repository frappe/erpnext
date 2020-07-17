# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

def execute():

	frappe.reload_doc('accounts', 'doctype', 'bank_account')
	frappe.reload_doc('accounts', 'doctype', 'bank')

	if frappe.db.has_column('Bank', 'branch_code') and frappe.db.has_column('Bank Account', 'branch_code'):
		frappe.db.sql("""UPDATE `tabBank` b, `tabBank Account` ba
			SET ba.branch_code = b.branch_code
			WHERE ba.bank = b.name AND
			ifnull(b.branch_code, '') != '' AND ifnull(ba.branch_code, '') = ''""")