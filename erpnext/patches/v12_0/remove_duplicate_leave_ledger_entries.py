# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe


def execute():
	"""Delete duplicate leave ledger entries of type allocation created."""
	frappe.reload_doc('hr', 'doctype', 'leave_ledger_entry')
	if not frappe.db.a_row_exists("Leave Ledger Entry"):
		return

	duplicate_records_list = get_duplicate_records()
	delete_duplicate_ledger_entries(duplicate_records_list)

def get_duplicate_records():
	"""Fetch all but one duplicate records from the list of expired leave allocation."""
	return frappe.db.sql("""
		SELECT name, employee, transaction_name, leave_type, is_carry_forward, from_date, to_date
		FROM `tabLeave Ledger Entry`
		WHERE
			transaction_type = 'Leave Allocation'
			AND docstatus = 1
			AND is_expired = 1
		GROUP BY
			employee, transaction_name, leave_type, is_carry_forward, from_date, to_date
		HAVING
			count(name) > 1
		ORDER BY
			creation
	""")

def delete_duplicate_ledger_entries(duplicate_records_list):
	"""Delete duplicate leave ledger entries."""
	if not duplicate_records_list: return
	for d in duplicate_records_list:
		frappe.db.sql('''
			DELETE FROM `tabLeave Ledger Entry`
			WHERE name != %s
				AND employee = %s
				AND transaction_name = %s
				AND leave_type = %s
				AND is_carry_forward = %s
				AND from_date = %s
				AND to_date = %s
		''', tuple(d))
