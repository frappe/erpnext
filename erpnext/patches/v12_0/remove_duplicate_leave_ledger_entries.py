# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	"""Delete duplicate leave ledger entries of type allocation created."""
	if not frappe.db.a_row_exists("Leave Ledger Entry"):
		return

	duplicate_records_list = get_duplicate_records()
	delete_duplicate_ledger_entries(duplicate_records_list)

def get_duplicate_records():
	"""Fetch all but one duplicate records from the list of expired leave allocation."""
	return frappe.db.sql_list("""
		WITH duplicate_records AS
		(SELECT
			name, transaction_name, is_carry_forward,
			ROW_NUMBER() over(partition by transaction_name order by creation)as row
		FROM `tabLeave Ledger Entry` l
		WHERE (EXISTS
			(SELECT name
				FROM `tabLeave Ledger Entry`
				WHERE
					transaction_name = l.transaction_name
					AND transaction_type = 'Leave Allocation'
					AND name <> l.name
					AND employee = l.employee
					AND docstatus = 1
					AND leave_type = l.leave_type
					AND is_carry_forward=l.is_carry_forward
					AND to_date = l.to_date
					AND from_date = l.from_date
					AND is_expired = 1
		)))
		SELECT name FROM duplicate_records WHERE row > 1
	""")

def delete_duplicate_ledger_entries(duplicate_records_list):
	"""Delete duplicate leave ledger entries."""
	if not duplicate_records_list: return
	frappe.db.sql('''DELETE FROM `tabLeave Ledger Entry` WHERE name in %s''', ((tuple(duplicate_records_list)), ))