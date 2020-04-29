# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	''' Delete duplicate leave ledger entries of type allocation created '''
	if not frappe.db.a_row_exists("Leave Ledger Entry"):
		return

	delete_duplicate_ledger_entries()

def delete_duplicate_ledger_entries():
	''' Delete duplicate ledger entries of transaction type allocation '''
	frappe.db.sql("""
		WITH duplicate_records AS
		(SELECT
			name, transaction_name, is_carry_forward,
			ROW_NUMBER() over(partition by transaction_name order by name)as row
		FROM `tabLeave Ledger Entry` l
		WHERE (EXISTS
			(SELECT name
				FROM `tabLeave Ledger Entry`
				WHERE
					transaction_name = l.transaction_name
					AND transaction_type = 'Leave Allocation'
					AND name<>l.name
					AND employee = l.employee
					AND leave_type = l.leave_type
					AND is_carry_forward=l.is_carry_forward
					AND to_date = l.to_date
					AND from_date = l.from_date
					AND is_expired = 1
		)))
		DELETE name, row, transaction_name FROM duplicate_records WHERE row > 1
	""")