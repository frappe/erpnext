# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, today

def execute():
	""" Generates leave ledger entries for leave allocation/application/encashment
		for last allocation """
	if not frappe.get_meta("Journal Entry Account").has_field("bank_account"):
		frappe.reload_doc("Accounts", "doctype", "Journal Entry Account")
		update_journal_entry_account_fieldname()

def update_journal_entry_account_fieldname():
	''' maps data from old field to the new field '''
	frappe.db.sql("""
		UPDATE `tabJournal Entry Account`
		SET `bank_account` = `bank_account_no`
	""")