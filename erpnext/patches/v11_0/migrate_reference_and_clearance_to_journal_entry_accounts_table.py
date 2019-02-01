# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils.global_search import rebuild_for_doctype

def execute():
	frappe.reload_doc("accounts", "doctype", "journal_entry")
	frappe.reload_doc("accounts", "doctype", "journal_entry_account")
	frappe.reload_doc("stock", "doctype", "stock_entry")

	# Migrate clearance_date for only Bank and Cash accounts
	frappe.db.sql("""
		update `tabJournal Entry Account` jvd
		inner join `tabJournal Entry` jv on jv.name = jvd.parent
		inner join `tabAccount` acc on acc.name = jvd.account
		set jvd.clearance_date = jv.clearance_date
		where acc.account_type = 'Bank' or acc.account_type = 'Cash'
	""")

	# Migrate reference_no and reference_date for all account types
	frappe.db.sql("""
		update `tabJournal Entry Account` jvd
		inner join `tabJournal Entry` jv on jv.name = jvd.parent
		set jvd.cheque_no = jv.cheque_no, jvd.cheque_date = jv.cheque_date
	""")

	# Set reference_numbers = cheque_no since we can assume no Journal Entry will have multiple cheque_nos
	frappe.db.sql("""update `tabJournal Entry` set reference_numbers = cheque_no""")

	# Rebuild global search, not sure if this is necessary
	rebuild_for_doctype("Journal Entry")
	rebuild_for_doctype("Payment Entry")
	rebuild_for_doctype("Stock Entry")