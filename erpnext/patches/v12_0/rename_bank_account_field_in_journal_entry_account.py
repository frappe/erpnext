# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	"""Change the fieldname from bank_account_no to bank_account"""
	if not frappe.get_meta("Journal Entry Account").has_field("bank_account"):
		frappe.reload_doc("Accounts", "doctype", "Journal Entry Account")
		update_journal_entry_account_fieldname()


def update_journal_entry_account_fieldname():
	"""maps data from old field to the new field"""
	if frappe.db.has_column("Journal Entry Account", "bank_account_no"):
		rename_field("Journal Entry Account", "bank_account_no", "bank_account")
