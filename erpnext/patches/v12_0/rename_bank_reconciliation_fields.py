# Copyright (c) 2020, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def _rename_single_field(**kwargs):
	count = frappe.db.sql("SELECT COUNT(*) FROM tabSingles WHERE doctype='{doctype}' AND field='{new_name}';".format(**kwargs))[0][0] #nosec
	if count == 0:
		frappe.db.sql("UPDATE tabSingles SET field='{new_name}' WHERE doctype='{doctype}' AND field='{old_name}';".format(**kwargs)) #nosec

def execute():
	BR  = "Bank Reconciliation"
	AC  = "account"
	BA  = "bank_account"
	BAN = "bank_account_no"

	_rename_single_field(doctype = BR, old_name = BA , new_name = AC)
	_rename_single_field(doctype = BR, old_name = BAN, new_name = BA)
	frappe.reload_doc("Accounts", "doctype", BR)
