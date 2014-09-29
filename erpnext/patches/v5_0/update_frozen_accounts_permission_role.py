# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	account_settings = frappe.get_doc("Accounts Settings")

	if not account_settings.frozen_accounts_modifier and account_settings.bde_auth_role:
		account_settings.frozen_accounts_modifier = account_settings.bde_auth_role

	account_settings.save()
