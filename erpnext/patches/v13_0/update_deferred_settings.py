# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals
import frappe

def execute():
	accounts_settings = frappe.get_doc('Accounts Settings', 'Accounts Settings')
	accounts_settings.book_deferred_entries_based_on = 'Days'
	accounts_settings.book_deferred_entries_via_journal_entry = 'No'
	accounts_settings.submit_journal_entries = 'No'
	accounts_settings.save()