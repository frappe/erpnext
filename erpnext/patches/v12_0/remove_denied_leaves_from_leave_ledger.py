# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe


def execute():
	''' Delete leave ledger entry created
		via leave applications with status != Approved '''
	if not frappe.db.a_row_exists("Leave Ledger Entry"):
		return

	leave_application_list = get_denied_leave_application_list()
	if leave_application_list:
		delete_denied_leaves_from_leave_ledger_entry(leave_application_list)

def get_denied_leave_application_list():
	return frappe.db.sql_list(''' Select name from `tabLeave Application` where status <> 'Approved' ''')

def delete_denied_leaves_from_leave_ledger_entry(leave_application_list):
	if leave_application_list:
		frappe.db.sql(''' Delete
			FROM `tabLeave Ledger Entry`
			WHERE
				transaction_type = 'Leave Application'
				AND transaction_name in (%s) ''' % (', '.join(['%s'] * len(leave_application_list))), #nosec
				tuple(leave_application_list))
