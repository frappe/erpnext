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
	duplicate_records = frappe.db.sql("""
		SELECT
			name, transaction_name
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
		))
		ORDER BY creation
	""", as_dict=1)
	new_records = {}
	repeated_records = []
	for record in duplicate_records:
		# generates a new key as transaction name within the new record,
		# if record is already processed add remaining names in the repeated records
		if not new_records.get(record.transaction_name):
			new_records.setdefault(record.transaction_name, []).append(record)
		else:
			repeated_records.append(record.name)

	return repeated_records

def delete_duplicate_ledger_entries(duplicate_records_list):
	"""Delete duplicate leave ledger entries."""
	if duplicate_records_list:
		frappe.db.sql(''' DELETE FROM `tabLeave Ledger Entry` WHERE name in {0}'''.format(tuple(duplicate_records_list))) #nosec