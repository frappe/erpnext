# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	account_settings = frappe.get_doc("Accounts Settings")

	if not account_settings.frozen_accounts_modifier and account_settings.bde_auth_role:
		frappe.db.set_value("Accounts Settings", None,
			"frozen_accounts_modifier", account_settings.bde_auth_role)

